import logging
from dataclasses import dataclass
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)

from app.domain.conversation_manager import (
    ConversationManager,
)
from app.llm.client import LLMClient
from app.llm.exceptions import LLMError
from app.llm.models import (
    LLMMessage,
    LLMUsage,
)
from app.prompts.conversation_summary import (
    build_conversation_summary_messages,
)


logger = logging.getLogger(
    "uvicorn.error.memory"
)


class _SummaryPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    summary: str = Field(
        min_length=1,
        max_length=6000,
    )


@dataclass(frozen=True, slots=True)
class ConversationMemoryContext:
    summary: str | None
    messages: tuple[LLMMessage, ...]
    source_message_count: int
    context_truncated: bool


@dataclass(frozen=True, slots=True)
class MemoryCompactionResult:
    status: Literal[
        "not_needed",
        "updated",
        "failed",
    ]

    messages_summarized: int = 0
    usage: LLMUsage | None = None
    duration_ms: int | None = None


class ConversationMemoryService:
    """Build and compact public conversation memory."""

    def __init__(
        self,
        *,
        manager: ConversationManager,
        llm_client: LLMClient,
        recent_message_limit: int,
        summary_trigger_messages: int,
        context_char_budget: int,
    ) -> None:
        if (
            summary_trigger_messages
            <= recent_message_limit
        ):
            raise ValueError(
                "summary trigger must be greater "
                "than recent message limit"
            )

        self._manager = manager
        self._llm_client = llm_client
        self._recent_message_limit = (
            recent_message_limit
        )
        self._summary_trigger_messages = (
            summary_trigger_messages
        )
        self._context_char_budget = (
            context_char_budget
        )

    def load_context(
        self,
        conversation_id: int,
    ) -> ConversationMemoryContext:
        conversation = (
            self._manager.get_conversation(
                conversation_id
            )
        )

        messages = self._manager.list_messages(
            conversation_id,
            after_message_id=(
                conversation
                .summarized_through_message_id
            ),
        )

        selected_messages = []
        used_characters = len(
            conversation.summary or ""
        )

        for message in reversed(messages):
            message_size = len(
                message.content
            )

            if (
                selected_messages
                and used_characters
                + message_size
                > self._context_char_budget
            ):
                break

            selected_messages.append(
                message
            )
            used_characters += message_size

        selected_messages.reverse()

        return ConversationMemoryContext(
            summary=conversation.summary,
            messages=tuple(
                LLMMessage(
                    role=message.role.value,
                    content=message.content,
                )
                for message
                in selected_messages
            ),
            source_message_count=len(
                selected_messages
            ),
            context_truncated=(
                len(selected_messages)
                < len(messages)
            ),
        )

    def record_turn_and_compact(
        self,
        *,
        conversation_id: int,
        user_content: str,
        assistant_content: str,
    ) -> MemoryCompactionResult:
        self._manager.append_turn(
            conversation_id,
            user_content=user_content,
            assistant_content=(
                assistant_content
            ),
        )

        return self.compact_if_needed(
            conversation_id
        )

    def compact_if_needed(
        self,
        conversation_id: int,
    ) -> MemoryCompactionResult:
        conversation = (
            self._manager.get_conversation(
                conversation_id
            )
        )

        messages = self._manager.list_messages(
            conversation_id,
            after_message_id=(
                conversation
                .summarized_through_message_id
            ),
        )

        total_characters = sum(
            len(message.content)
            for message in messages
        )

        needs_compaction = (
            len(messages)
            > self._summary_trigger_messages
            or total_characters
            > self._context_char_budget
        )

        if not needs_compaction:
            return MemoryCompactionResult(
                status="not_needed"
            )

        keep_count = min(
            self._recent_message_limit,
            len(messages),
        )

        while (
            keep_count > 2
            and sum(
                len(message.content)
                for message
                in messages[-keep_count:]
            )
            > self._context_char_budget
        ):
            keep_count -= 1

        messages_to_summarize = (
            messages[:-keep_count]
        )

        if not messages_to_summarize:
            return MemoryCompactionResult(
                status="not_needed"
            )

        try:
            llm_result = (
                self._llm_client.generate_json(
                    messages=(
                        build_conversation_summary_messages(
                            existing_summary=(
                                conversation.summary
                            ),
                            messages=(
                                messages_to_summarize
                            ),
                        )
                    )
                )
            )

            summary_payload = (
                _SummaryPayload
                .model_validate_json(
                    llm_result.content
                )
            )

        except (
            LLMError,
            ValidationError,
        ) as error:
            logger.warning(
                "conversation_summary_failed "
                "conversation_id=%d "
                "error_type=%s",
                conversation_id,
                type(error).__name__,
            )

            return MemoryCompactionResult(
                status="failed",
                messages_summarized=0,
            )

        last_message = (
            messages_to_summarize[-1]
        )

        self._manager.update_summary(
            conversation_id,
            summary=summary_payload.summary,
            summarized_through_message_id=(
                last_message.id
            ),
        )

        logger.info(
            "conversation_summary_updated "
            "conversation_id=%d "
            "messages_summarized=%d "
            "duration_ms=%d total_tokens=%d",
            conversation_id,
            len(messages_to_summarize),
            llm_result.duration_ms,
            llm_result.usage.total_tokens,
        )

        return MemoryCompactionResult(
            status="updated",
            messages_summarized=len(
                messages_to_summarize
            ),
            usage=llm_result.usage,
            duration_ms=(
                llm_result.duration_ms
            ),
        )

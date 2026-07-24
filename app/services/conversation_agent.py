from dataclasses import dataclass

from app.agent.models import (
    AgentRunResult,
)
from app.services.agent_runner import (
    AgentRunner,
)
from app.services.conversation_memory import (
    ConversationMemoryService,
    MemoryCompactionResult,
)


@dataclass(frozen=True, slots=True)
class ConversationAgentRunResult:
    conversation_id: int
    agent_result: AgentRunResult
    history_messages_used: int
    summary_used: bool
    context_truncated: bool
    compaction: MemoryCompactionResult


class ConversationAgentService:
    """Run an Agent with persistent public memory."""

    def __init__(
        self,
        *,
        runner: AgentRunner,
        memory: ConversationMemoryService,
    ) -> None:
        self._runner = runner
        self._memory = memory

    def run(
        self,
        *,
        conversation_id: int,
        user_request: str,
        max_steps: int,
    ) -> ConversationAgentRunResult:
        context = self._memory.load_context(
            conversation_id
        )

        agent_result = self._runner.run(
            user_request=user_request,
            max_steps=max_steps,
            history_messages=list(
                context.messages
            ),
            memory_summary=context.summary,
        )

        compaction = (
            self._memory
            .record_turn_and_compact(
                conversation_id=(
                    conversation_id
                ),
                user_content=user_request,
                assistant_content=(
                    agent_result.final_answer
                ),
            )
        )

        return ConversationAgentRunResult(
            conversation_id=conversation_id,
            agent_result=agent_result,
            history_messages_used=(
                context.source_message_count
            ),
            summary_used=(
                context.summary is not None
            ),
            context_truncated=(
                context.context_truncated
            ),
            compaction=compaction,
        )

from app.domain.conversation import (
    Conversation,
    ConversationMessage,
)
from app.domain.exceptions import (
    ConversationNotFoundError,
)
from app.domain.repositories import (
    ConversationRepository,
)


class ConversationManager:
    """Manage persistent public conversations."""

    def __init__(
        self,
        repository: ConversationRepository,
    ) -> None:
        self._repository = repository

    def create_conversation(
        self,
        *,
        title: str | None = None,
    ) -> Conversation:
        normalized_title = (
            title.strip()
            if title is not None
            else None
        )

        if normalized_title == "":
            normalized_title = None

        return self._repository.create(
            title=normalized_title,
        )

    def get_conversation(
        self,
        conversation_id: int,
    ) -> Conversation:
        conversation = self._repository.get(
            conversation_id
        )

        if conversation is None:
            raise ConversationNotFoundError(
                "conversation "
                f"{conversation_id} was not found"
            )

        return conversation

    def list_messages(
        self,
        conversation_id: int,
        *,
        after_message_id: int | None = None,
    ) -> list[ConversationMessage]:
        self.get_conversation(
            conversation_id
        )

        return self._repository.list_messages(
            conversation_id,
            after_message_id=(
                after_message_id
            ),
        )

    def append_turn(
        self,
        conversation_id: int,
        *,
        user_content: str,
        assistant_content: str,
    ) -> tuple[
        ConversationMessage,
        ConversationMessage,
    ]:
        user_content = user_content.strip()
        assistant_content = (
            assistant_content.strip()
        )

        if not user_content:
            raise ValueError(
                "user content cannot be empty"
            )

        if not assistant_content:
            raise ValueError(
                "assistant content cannot be empty"
            )

        messages = self._repository.append_turn(
            conversation_id,
            user_content=user_content,
            assistant_content=(
                assistant_content
            ),
        )

        if messages is None:
            raise ConversationNotFoundError(
                "conversation "
                f"{conversation_id} was not found"
            )

        return messages

    def update_summary(
        self,
        conversation_id: int,
        *,
        summary: str,
        summarized_through_message_id: int,
    ) -> Conversation:
        summary = summary.strip()

        if not summary:
            raise ValueError(
                "summary cannot be empty"
            )

        conversation = (
            self._repository.update_summary(
                conversation_id,
                summary=summary,
                summarized_through_message_id=(
                    summarized_through_message_id
                ),
            )
        )

        if conversation is None:
            raise ConversationNotFoundError(
                "conversation "
                f"{conversation_id} was not found"
            )

        return conversation

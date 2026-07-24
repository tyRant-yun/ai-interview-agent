from app.domain.conversation import (
    Conversation,
    ConversationMessage,
    ConversationRole,
)
from typing import Protocol

from app.domain.models import MasteryLevel, Note


class NoteRepository(Protocol):
    """Storage contract required by NoteManager."""

    def create(
        self,
        *,
        title: str,
        category: str,
        content: str,
        mastery_level: MasteryLevel,
    ) -> Note:
        ...

    def list(
        self,
        *,
        category: str | None = None,
        mastery_level: MasteryLevel | None = None,
    ) -> list[Note]:
        ...

    def get(self, note_id: int) -> Note | None:
        ...

    def update(
        self,
        note_id: int,
        *,
        title: str,
        category: str,
        content: str,
        mastery_level: MasteryLevel,
    ) -> Note | None:
        ...

    def delete(self, note_id: int) -> bool:
        ...

    def title_exists(
        self,
        title: str,
        *,
        exclude_note_id: int | None = None,
    ) -> bool:
        ...

class ConversationRepository(Protocol):
    """Storage contract for conversation memory."""

    def create(
        self,
        *,
        title: str | None,
    ) -> Conversation:
        ...

    def get(
        self,
        conversation_id: int,
    ) -> Conversation | None:
        ...

    def list_messages(
        self,
        conversation_id: int,
        *,
        after_message_id: int | None = None,
    ) -> list[ConversationMessage]:
        ...

    def append_turn(
        self,
        conversation_id: int,
        *,
        user_content: str,
        assistant_content: str,
    ) -> tuple[
        ConversationMessage,
        ConversationMessage,
    ] | None:
        ...

    def update_summary(
        self,
        conversation_id: int,
        *,
        summary: str,
        summarized_through_message_id: int,
    ) -> Conversation | None:
        ...

from dataclasses import dataclass
from enum import Enum


class ConversationRole(str, Enum):
    """Public roles persisted in conversation memory."""

    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class Conversation:
    """One persistent public conversation."""

    id: int
    title: str | None
    summary: str | None
    summarized_through_message_id: int | None


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    """One persisted public conversation message."""

    id: int
    conversation_id: int
    role: ConversationRole
    content: str

class NoteError(Exception):
    """Base exception for note-related business errors."""


class NoteNotFoundError(NoteError):
    """Raised when a requested note does not exist."""


class DuplicateNoteError(NoteError):
    """Raised when a note with the same title already exists."""

class ConversationError(Exception):
    """Base exception for conversation errors."""


class ConversationNotFoundError(
    ConversationError
):
    """Raised when a conversation does not exist."""

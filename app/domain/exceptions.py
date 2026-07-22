class NoteError(Exception):
    """Base exception for note-related business errors."""


class NoteNotFoundError(NoteError):
    """Raised when a requested note does not exist."""


class DuplicateNoteError(NoteError):
    """Raised when a note with the same title already exists."""

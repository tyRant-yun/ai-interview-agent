from app.domain.exceptions import (
    DuplicateNoteError,
    NoteNotFoundError,
)
from app.domain.models import MasteryLevel, Note
from app.domain.repositories import NoteRepository


class NoteManager:
    """Business rules for managing knowledge notes."""

    def __init__(
        self,
        repository: NoteRepository,
    ) -> None:
        self._repository = repository

    def create_note(
        self,
        *,
        title: str,
        category: str,
        content: str,
        mastery_level: MasteryLevel = MasteryLevel.NEW,
    ) -> Note:
        if self._repository.title_exists(title):
            raise DuplicateNoteError(
                f"a note with title {title!r} already exists"
            )

        return self._repository.create(
            title=title,
            category=category,
            content=content,
            mastery_level=mastery_level,
        )

    def list_notes(
        self,
        *,
        category: str | None = None,
        mastery_level: MasteryLevel | None = None,
    ) -> list[Note]:
        return self._repository.list(
            category=category,
            mastery_level=mastery_level,
        )

    def get_note(self, note_id: int) -> Note:
        note = self._repository.get(note_id)

        if note is None:
            raise NoteNotFoundError(
                f"note with id {note_id} was not found"
            )

        return note

    def update_note(
        self,
        note_id: int,
        *,
        title: str,
        category: str,
        content: str,
        mastery_level: MasteryLevel,
    ) -> Note:
        self.get_note(note_id)

        if self._repository.title_exists(
            title,
            exclude_note_id=note_id,
        ):
            raise DuplicateNoteError(
                f"a note with title {title!r} already exists"
            )

        note = self._repository.update(
            note_id,
            title=title,
            category=category,
            content=content,
            mastery_level=mastery_level,
        )

        if note is None:
            raise NoteNotFoundError(
                f"note with id {note_id} was not found"
            )

        return note

    def update_mastery(
        self,
        note_id: int,
        mastery_level: MasteryLevel,
    ) -> Note:
        existing_note = self.get_note(note_id)

        note = self._repository.update(
            note_id,
            title=existing_note.title,
            category=existing_note.category,
            content=existing_note.content,
            mastery_level=mastery_level,
        )

        if note is None:
            raise NoteNotFoundError(
                f"note with id {note_id} was not found"
            )

        return note

    def delete_note(self, note_id: int) -> None:
        deleted = self._repository.delete(note_id)

        if not deleted:
            raise NoteNotFoundError(
                f"note with id {note_id} was not found"
            )

from app.domain.exceptions import DuplicateNoteError, NoteNotFoundError
from app.domain.models import MasteryLevel, Note


class NoteManager:
    """In-memory note management service.

    The dictionary is temporary. It will be replaced by SQLite later.
    """

    def __init__(self) -> None:
        self._notes: dict[int, Note] = {}
        self._next_id = 1

    def create_note(
        self,
        *,
        title: str,
        category: str,
        content: str,
        mastery_level: MasteryLevel = MasteryLevel.NEW,
    ) -> Note:
        if self._title_exists(title):
            raise DuplicateNoteError(
                f"a note with title {title!r} already exists"
            )

        note = Note(
            id=self._next_id,
            title=title,
            category=category,
            content=content,
            mastery_level=mastery_level,
        )

        self._notes[note.id] = note
        self._next_id += 1
        return note

    def list_notes(
        self,
        *,
        category: str | None = None,
        mastery_level: MasteryLevel | None = None,
    ) -> list[Note]:
        notes = list(self._notes.values())

        if category is not None:
            normalized_category = category.strip().lower()
            notes = [
                note
                for note in notes
                if note.category.lower() == normalized_category
            ]

        if mastery_level is not None:
            notes = [
                note
                for note in notes
                if note.mastery_level == mastery_level
            ]

        return notes

    def get_note(self, note_id: int) -> Note:
        try:
            return self._notes[note_id]
        except KeyError as error:
            raise NoteNotFoundError(
                f"note with id {note_id} was not found"
            ) from error

    def update_mastery(
        self,
        note_id: int,
        mastery_level: MasteryLevel,
    ) -> Note:
        note = self.get_note(note_id)
        note.mastery_level = mastery_level
        return note

    def delete_note(self, note_id: int) -> None:
        self.get_note(note_id)
        del self._notes[note_id]

    def _title_exists(self, title: str) -> bool:
        normalized_title = title.strip().lower()
        return any(
            note.title.lower() == normalized_title
            for note in self._notes.values()
        )

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import NoteRecord
from app.domain.exceptions import DuplicateNoteError
from app.domain.models import MasteryLevel, Note


class SQLAlchemyNoteRepository:
    """Store and retrieve notes through SQLAlchemy."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(
        self,
        *,
        title: str,
        category: str,
        content: str,
        mastery_level: MasteryLevel,
    ) -> Note:
        record = NoteRecord(
            title=title,
            category=category,
            content=content,
            mastery_level=mastery_level.value,
        )

        self._session.add(record)

        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            raise DuplicateNoteError(
                f"a note with title {title!r} already exists"
            ) from error

        self._session.refresh(record)
        return self._to_domain(record)

    def list(
        self,
        *,
        category: str | None = None,
        mastery_level: MasteryLevel | None = None,
    ) -> list[Note]:
        statement = select(NoteRecord).order_by(NoteRecord.id)

        if category is not None:
            statement = statement.where(
                func.lower(NoteRecord.category)
                == category.strip().lower()
            )

        if mastery_level is not None:
            statement = statement.where(
                NoteRecord.mastery_level
                == mastery_level.value
            )

        records = self._session.scalars(statement).all()

        return [
            self._to_domain(record)
            for record in records
        ]

    def get(self, note_id: int) -> Note | None:
        record = self._session.get(NoteRecord, note_id)

        if record is None:
            return None

        return self._to_domain(record)

    def update(
        self,
        note_id: int,
        *,
        title: str,
        category: str,
        content: str,
        mastery_level: MasteryLevel,
    ) -> Note | None:
        record = self._session.get(NoteRecord, note_id)

        if record is None:
            return None

        record.title = title
        record.category = category
        record.content = content
        record.mastery_level = mastery_level.value

        try:
            self._session.commit()
        except IntegrityError as error:
            self._session.rollback()
            raise DuplicateNoteError(
                f"a note with title {title!r} already exists"
            ) from error

        self._session.refresh(record)
        return self._to_domain(record)

    def delete(self, note_id: int) -> bool:
        record = self._session.get(NoteRecord, note_id)

        if record is None:
            return False

        self._session.delete(record)

        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        return True

    def title_exists(
        self,
        title: str,
        *,
        exclude_note_id: int | None = None,
    ) -> bool:
        normalized_title = title.strip().lower()

        statement = select(NoteRecord.id).where(
            func.lower(NoteRecord.title)
            == normalized_title
        )

        if exclude_note_id is not None:
            statement = statement.where(
                NoteRecord.id != exclude_note_id
            )

        return (
            self._session.scalar(statement.limit(1))
            is not None
        )

    @staticmethod
    def _to_domain(record: NoteRecord) -> Note:
        return Note(
            id=record.id,
            title=record.title,
            category=record.category,
            content=record.content,
            mastery_level=MasteryLevel(
                record.mastery_level
            ),
        )

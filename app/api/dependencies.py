from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.domain.note_manager import NoteManager
from app.repositories.sqlalchemy_note_repository import (
    SQLAlchemyNoteRepository,
)


def get_note_manager(
    session: Session = Depends(get_session),
) -> NoteManager:
    repository = SQLAlchemyNoteRepository(session)
    return NoteManager(repository)


NoteManagerDependency = Annotated[
    NoteManager,
    Depends(get_note_manager),
]

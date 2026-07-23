from app.db.init_db import create_db_and_tables
from app.db.session import SessionLocal
from app.domain.models import MasteryLevel, Note
from app.domain.note_manager import NoteManager
from app.repositories.sqlalchemy_note_repository import (
    SQLAlchemyNoteRepository,
)

def print_note(note: Note) -> None:
    print(
        f"[{note.id}] {note.title} "
        f"| category={note.category} "
        f"| mastery={note.mastery_level.value}"
    )
    print(f"    {note.content}")

def main() -> None:
    create_db_and_tables()

    with SessionLocal() as session:
        repository = SQLAlchemyNoteRepository(session)
        manager = NoteManager(repository)

        if not manager.list_notes():
            manager.create_note(
                title="TCP three-way handshake",
                category="computer-network",
                content=(
                    "TCP uses SYN, SYN-ACK and ACK "
                    "to establish a connection."
                ),
                mastery_level=MasteryLevel.LEARNING,
            )

        for note in manager.list_notes():
            print_note(note)


if __name__ == "__main__":
    main()

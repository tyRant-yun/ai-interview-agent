from app.domain.exceptions import NoteError
from app.domain.models import MasteryLevel, Note
from app.domain.note_manager import NoteManager


def print_note(note: Note) -> None:
    print(
        f"[{note.id}] {note.title} "
        f"| category={note.category} "
        f"| mastery={note.mastery_level.value}"
    )
    print(f"    {note.content}")


def seed_notes(manager: NoteManager) -> None:
    manager.create_note(
        title="TCP three-way handshake",
        category="computer-network",
        content=(
            "The handshake synchronizes sequence numbers "
            "and confirms bidirectional communication."
        ),
    )

    manager.create_note(
        title="MySQL B+ tree index",
        category="mysql",
        content=(
            "B+ trees support ordered traversal and reduce "
            "the number of disk I/O operations."
        ),
        mastery_level=MasteryLevel.LEARNING,
    )


def main() -> None:
    manager = NoteManager()

    try:
        seed_notes(manager)

        print("All notes:")
        for note in manager.list_notes():
            print_note(note)

        print("\nUpdating note 1:")
        updated_note = manager.update_mastery(
            1,
            MasteryLevel.FAMILIAR,
        )
        print_note(updated_note)

        print("\nComputer network notes:")
        for note in manager.list_notes(category="computer-network"):
            print_note(note)

        print("\nDeleting note 2:")
        manager.delete_note(2)

        print("\nRemaining notes:")
        for note in manager.list_notes():
            print_note(note)

    except (NoteError, ValueError) as error:
        print(f"Operation failed: {error}")


if __name__ == "__main__":
    main()

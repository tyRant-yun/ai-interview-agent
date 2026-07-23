import pytest

from app.domain.models import (
    MasteryLevel,
    Note,
)
from app.domain.note_manager import NoteManager
from app.llm.models import LLMToolCall
from app.tools.exceptions import (
    ToolArgumentsError,
    ToolNotRegisteredError,
)
from app.tools.note_tools import build_note_tools
from app.tools.registry import ToolRegistry


class StubNoteRepository:
    """Minimal in-memory repository for Tool Registry tests."""

    def __init__(
        self,
        notes: list[Note],
    ) -> None:
        self._notes = {
            note.id: note
            for note in notes
        }

    def list(
        self,
        *,
        category: str | None = None,
        mastery_level: MasteryLevel | None = None,
    ) -> list[Note]:
        notes = list(self._notes.values())

        if category is not None:
            normalized_category = (
                category.strip().casefold()
            )

            notes = [
                note
                for note in notes
                if note.category.casefold()
                == normalized_category
            ]

        if mastery_level is not None:
            notes = [
                note
                for note in notes
                if note.mastery_level
                == mastery_level
            ]

        return notes

    def get(
        self,
        note_id: int,
    ) -> Note | None:
        return self._notes.get(note_id)

    # The following methods are not used in these tests,
    # but are included to satisfy the repository contract.

    def create(
        self,
        *,
        title: str,
        category: str,
        content: str,
        mastery_level: MasteryLevel,
    ) -> Note:
        raise NotImplementedError

    def update(
        self,
        note_id: int,
        *,
        title: str,
        category: str,
        content: str,
        mastery_level: MasteryLevel,
    ) -> Note | None:
        raise NotImplementedError

    def delete(
        self,
        note_id: int,
    ) -> bool:
        raise NotImplementedError

    def title_exists(
        self,
        title: str,
        *,
        exclude_note_id: int | None = None,
    ) -> bool:
        normalized_title = (
            title.strip().casefold()
        )

        return any(
            note.id != exclude_note_id
            and note.title.casefold()
            == normalized_title
            for note in self._notes.values()
        )


def build_manager() -> NoteManager:
    repository = StubNoteRepository(
        [
            Note(
                id=1,
                title="TCP three-way handshake",
                category="computer-network",
                content=(
                    "TCP uses SYN, SYN-ACK and ACK "
                    "to establish a connection."
                ),
                mastery_level=MasteryLevel.LEARNING,
            ),
            Note(
                id=2,
                title="HTTP request lifecycle",
                category="computer-network",
                content=(
                    "An HTTP request passes through "
                    "the web server and application."
                ),
                mastery_level=MasteryLevel.NEW,
            ),
            Note(
                id=3,
                title="MySQL B+ tree",
                category="mysql",
                content=(
                    "B+ trees reduce disk I/O and "
                    "support ordered traversal."
                ),
                mastery_level=MasteryLevel.MASTERED,
            ),
        ]
    )

    return NoteManager(repository)


def build_registry() -> ToolRegistry:
    manager = build_manager()

    return ToolRegistry(
        build_note_tools(manager)
    )


def test_registry_contains_three_note_tools():
    registry = build_registry()

    definitions = registry.definitions()

    assert [
        definition.name
        for definition in definitions
    ] == [
        "get_note",
        "search_notes",
        "get_weak_topics",
    ]


def test_search_notes_definition_has_json_schema():
    registry = build_registry()

    definition = next(
        definition
        for definition in registry.definitions()
        if definition.name == "search_notes"
    )

    schema = definition.parameters

    assert schema["type"] == "object"

    assert set(
        schema["properties"]
    ) == {
        "query",
        "category",
        "limit",
    }

    assert "query" in schema["required"]

    assert schema[
        "additionalProperties"
    ] is False


def test_registry_executes_search_notes():
    registry = build_registry()

    outcome = registry.execute(
        LLMToolCall(
            id="call-search-1",
            name="search_notes",
            arguments_json=(
                "{"
                '"query":"TCP",'
                '"category":"computer-network",'
                '"limit":5'
                "}"
            ),
        )
    )

    assert outcome.success is True
    assert outcome.tool_name == "search_notes"
    assert outcome.call_id == "call-search-1"

    assert outcome.output["count"] == 1

    assert outcome.output["notes"][0][
        "title"
    ] == "TCP three-way handshake"


def test_registry_rejects_unregistered_tool():
    registry = build_registry()

    with pytest.raises(
        ToolNotRegisteredError
    ):
        registry.execute(
            LLMToolCall(
                id="call-unknown-1",
                name="delete_all_notes",
                arguments_json="{}",
            )
        )


def test_registry_rejects_invalid_arguments():
    registry = build_registry()

    # search_notes requires a non-empty query.
    with pytest.raises(
        ToolArgumentsError
    ):
        registry.execute(
            LLMToolCall(
                id="call-invalid-1",
                name="search_notes",
                arguments_json=(
                    '{"limit":5}'
                ),
            )
        )


def test_missing_note_returns_failed_outcome():
    registry = build_registry()

    outcome = registry.execute(
        LLMToolCall(
            id="call-get-999",
            name="get_note",
            arguments_json=(
                '{"note_id":999}'
            ),
        )
    )

    assert outcome.success is False
    assert outcome.output is None
    assert outcome.error is not None
    assert "not found" in outcome.error

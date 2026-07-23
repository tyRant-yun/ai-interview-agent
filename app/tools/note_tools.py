from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.domain.models import (
    MasteryLevel,
    Note,
)
from app.domain.note_manager import NoteManager
from app.tools.registry import RegisteredTool


class GetNoteArguments(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    note_id: int = Field(gt=0)


class SearchNotesArguments(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(
        min_length=1,
        max_length=200,
    )

    category: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=10,
    )


class GetWeakTopicsArguments(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    category: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=10,
    )


def _serialize_note(
    note: Note,
    *,
    include_content: bool,
) -> dict[str, object]:
    result: dict[str, object] = {
        "id": note.id,
        "title": note.title,
        "category": note.category,
        "mastery_level": (
            note.mastery_level.value
        ),
    }

    if include_content:
        result["content"] = note.content

    return result


def build_note_tools(
    manager: NoteManager,
) -> list[RegisteredTool]:
    def get_note(
        arguments: BaseModel,
    ) -> dict[str, object]:
        assert isinstance(
            arguments,
            GetNoteArguments,
        )

        note = manager.get_note(
            arguments.note_id
        )

        return _serialize_note(
            note,
            include_content=True,
        )

    def search_notes(
        arguments: BaseModel,
    ) -> dict[str, object]:
        assert isinstance(
            arguments,
            SearchNotesArguments,
        )

        notes = manager.list_notes(
            category=arguments.category
        )

        normalized_query = (
            arguments.query.casefold()
        )

        matches = [
            note
            for note in notes
            if normalized_query
            in note.title.casefold()
            or normalized_query
            in note.content.casefold()
        ]

        limited_matches = matches[
            : arguments.limit
        ]

        return {
            "count": len(limited_matches),
            "notes": [
                _serialize_note(
                    note,
                    include_content=True,
                )
                for note in limited_matches
            ],
        }

    def get_weak_topics(
        arguments: BaseModel,
    ) -> dict[str, object]:
        assert isinstance(
            arguments,
            GetWeakTopicsArguments,
        )

        notes = manager.list_notes(
            category=arguments.category
        )

        weak_notes = [
            note
            for note in notes
            if note.mastery_level
            in {
                MasteryLevel.NEW,
                MasteryLevel.LEARNING,
            }
        ]

        weak_notes.sort(
            key=lambda note: (
                0
                if note.mastery_level
                == MasteryLevel.NEW
                else 1,
                note.id,
            )
        )

        limited_notes = weak_notes[
            : arguments.limit
        ]

        return {
            "count": len(limited_notes),
            "notes": [
                _serialize_note(
                    note,
                    include_content=False,
                )
                for note in limited_notes
            ],
        }

    return [
        RegisteredTool(
            name="get_note",
            description=(
                "Retrieve one knowledge note by "
                "its numeric note ID."
            ),
            arguments_model=(
                GetNoteArguments
            ),
            handler=get_note,
        ),
        RegisteredTool(
            name="search_notes",
            description=(
                "Search stored knowledge notes "
                "by words found in the title "
                "or content."
            ),
            arguments_model=(
                SearchNotesArguments
            ),
            handler=search_notes,
        ),
        RegisteredTool(
            name="get_weak_topics",
            description=(
                "List notes whose mastery level "
                "is new or learning."
            ),
            arguments_model=(
                GetWeakTopicsArguments
            ),
            handler=get_weak_topics,
        ),
    ]

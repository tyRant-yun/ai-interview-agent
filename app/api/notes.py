from fastapi import APIRouter, Query, Response, status

from app.api.dependencies import NoteManagerDependency
from app.api.schemas import (
    NoteCreate,
    NoteReplace,
    NoteResponse,
)
from app.domain.models import MasteryLevel


router = APIRouter(
    prefix="/notes",
    tags=["notes"],
)


@router.post(
    "",
    response_model=NoteResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_note(
    payload: NoteCreate,
    manager: NoteManagerDependency,
) -> NoteResponse:
    note = manager.create_note(
        **payload.model_dump()
    )

    return NoteResponse.model_validate(note)


@router.get(
    "",
    response_model=list[NoteResponse],
)
def list_notes(
    manager: NoteManagerDependency,
    category: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),
    mastery_level: MasteryLevel | None = None,
) -> list[NoteResponse]:
    notes = manager.list_notes(
        category=category,
        mastery_level=mastery_level,
    )

    return [
        NoteResponse.model_validate(note)
        for note in notes
    ]


@router.get(
    "/{note_id}",
    response_model=NoteResponse,
)
def get_note(
    note_id: int,
    manager: NoteManagerDependency,
) -> NoteResponse:
    note = manager.get_note(note_id)
    return NoteResponse.model_validate(note)


@router.put(
    "/{note_id}",
    response_model=NoteResponse,
)
def replace_note(
    note_id: int,
    payload: NoteReplace,
    manager: NoteManagerDependency,
) -> NoteResponse:
    note = manager.update_note(
        note_id,
        **payload.model_dump(),
    )

    return NoteResponse.model_validate(note)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_note(
    note_id: int,
    manager: NoteManagerDependency,
) -> Response:
    manager.delete_note(note_id)

    return Response(
        status_code=status.HTTP_204_NO_CONTENT
    )

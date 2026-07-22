from pydantic import BaseModel, ConfigDict, Field

from app.domain.models import MasteryLevel


class NotePayload(BaseModel):
    """Common validated fields for creating or replacing a note."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    title: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=10_000)
    mastery_level: MasteryLevel = MasteryLevel.NEW


class NoteCreate(NotePayload):
    """Request body for creating a note."""


class NoteReplace(NotePayload):
    """Request body for fully replacing a note."""


class NoteResponse(BaseModel):
    """Public API representation of a note."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    category: str
    content: str
    mastery_level: MasteryLevel

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


ToolContentContract = Literal[
    "plain_text",
    "final_answer_envelope",
]


class FinalAnswerEnvelope(BaseModel):
    """Provider-facing contract for one Agent final answer."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    answer: str = Field(min_length=1)


DSML_CONTROL_MARKER = "<｜｜DSML｜｜"


def contains_dsml_control_marker(
    content: str,
) -> bool:
    """Reject a known control delimiter without parsing it."""

    return DSML_CONTROL_MARKER in content

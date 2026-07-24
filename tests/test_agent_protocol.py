import pytest
from pydantic import ValidationError

from app.llm.agent_protocol import (
    FinalAnswerEnvelope,
    contains_dsml_control_marker,
)


def test_final_answer_envelope_is_strict():
    envelope = (
        FinalAnswerEnvelope.model_validate_json(
            '{"answer":"  useful answer  "}'
        )
    )

    assert envelope.answer == "useful answer"

    with pytest.raises(ValidationError):
        FinalAnswerEnvelope.model_validate_json(
            '{"answer":"ok","extra":true}'
        )


@pytest.mark.parametrize(
    "payload",
    [
        '{"answer":""}',
        '{"answer":"   "}',
        '{"answer":null}',
        '{"answer":42}',
        "[]",
    ],
)
def test_final_answer_envelope_rejects_invalid_answer(
    payload,
):
    with pytest.raises(ValidationError):
        FinalAnswerEnvelope.model_validate_json(
            payload
        )


def test_dsml_guard_only_matches_control_delimiter():
    assert contains_dsml_control_marker(
        "<｜｜DSML｜｜tool_calls>"
    )
    assert not contains_dsml_control_marker(
        "DSML is a protocol name."
    )
    assert not contains_dsml_control_marker(
        "get_note is an available tool."
    )

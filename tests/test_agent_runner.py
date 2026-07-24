import pytest
from pydantic import (
    BaseModel,
    ConfigDict,
)

from app.agent.exceptions import (
    AgentRepeatedToolCallError,
)
from app.llm.exceptions import (
    LLMInvalidResponseError,
    LLMToolDecisionProtocolError,
)
from app.llm.models import (
    LLMToolCall,
    LLMToolDecision,
    LLMUsage,
)
from app.services.agent_runner import AgentRunner
from app.tools.registry import (
    RegisteredTool,
    ToolRegistry,
)
from app.tools.exceptions import ToolSelectionError
from tests.fakes import FakeLLMClient


class EchoArguments(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    value: str
    label: str = ""


class GetNoteArguments(BaseModel):
    model_config = ConfigDict(
        extra="forbid"
    )

    note_id: int


def build_registry() -> ToolRegistry:
    def echo(arguments: BaseModel):
        assert isinstance(
            arguments,
            EchoArguments,
        )

        return {
            "value": arguments.value,
            "label": arguments.label,
        }

    return ToolRegistry(
        [
            RegisteredTool(
                name="echo",
                description=(
                    "Return the supplied value."
                ),
                arguments_model=EchoArguments,
                handler=echo,
            )
        ]
    )


def build_get_note_registry() -> ToolRegistry:
    def get_note(arguments: BaseModel):
        assert isinstance(
            arguments,
            GetNoteArguments,
        )

        return {
            "note_id": arguments.note_id,
        }

    return ToolRegistry(
        [
            RegisteredTool(
                name="get_note",
                description="Return one note.",
                arguments_model=GetNoteArguments,
                handler=get_note,
            )
        ]
    )


def decision_with_tool(
    *,
    call_id: str,
    value: str,
    arguments_json: str | None = None,
) -> LLMToolDecision:
    return LLMToolDecision(
        content=None,
        tool_calls=(
            LLMToolCall(
                id=call_id,
                name="echo",
                arguments_json=(
                    arguments_json
                    or f'{{"value":"{value}"}}'
                ),
            ),
        ),
        model="fake-model",
        usage=LLMUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
        duration_ms=5,
    )


def decision_with_get_note(
    *,
    call_id: str,
    note_id: int,
) -> LLMToolDecision:
    return LLMToolDecision(
        content=None,
        tool_calls=(
            LLMToolCall(
                id=call_id,
                name="get_note",
                arguments_json=(
                    f'{{"note_id":{note_id}}}'
                ),
            ),
        ),
        model="fake-model",
        usage=LLMUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
        duration_ms=5,
    )


def final_decision(
    text: str,
) -> LLMToolDecision:
    return LLMToolDecision(
        content=text,
        tool_calls=(),
        model="fake-model",
        usage=LLMUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
        duration_ms=5,
    )


def empty_decision() -> LLMToolDecision:
    return LLMToolDecision(
        content=None,
        tool_calls=(),
        model="fake-model",
        usage=LLMUsage(),
        duration_ms=5,
    )


def test_agent_can_answer_without_tool():
    fake = FakeLLMClient(
        "{}",
        tool_decisions=[
            final_decision(
                "TCP is a transport protocol."
            )
        ],
    )

    runner = AgentRunner(
        llm_client=fake,
        registry=build_registry(),
    )

    result = runner.run(
        user_request="What is TCP?",
        max_steps=4,
    )

    assert result.final_answer == (
        "TCP is a transport protocol."
    )

    assert len(result.steps) == 1
    assert result.steps[0].tool_call is None
    assert result.usage.total_tokens == 15


def test_agent_uses_tool_then_answers():
    fake = FakeLLMClient(
        "{}",
        tool_decisions=[
            decision_with_tool(
                call_id="call-1",
                value="TCP",
            ),
            final_decision(
                "The stored value is TCP."
            ),
        ],
    )

    runner = AgentRunner(
        llm_client=fake,
        registry=build_registry(),
    )

    result = runner.run(
        user_request="Inspect the stored value.",
        max_steps=2,
    )

    assert result.final_answer == (
        "The stored value is TCP."
    )

    assert len(result.steps) == 2

    first_step = result.steps[0]

    assert first_step.tool_call is not None
    assert first_step.tool_result is not None
    assert first_step.tool_result.success is True

    assert result.usage.total_tokens == 30
    assert fake.tool_choices == [
        "auto",
        "none",
    ]


def test_tool_result_is_returned_to_model():
    fake = FakeLLMClient(
        "{}",
        tool_decisions=[
            decision_with_tool(
                call_id="call-1",
                value="TCP",
            ),
            final_decision("done"),
        ],
    )

    runner = AgentRunner(
        llm_client=fake,
        registry=build_registry(),
    )

    runner.run(
        user_request="Inspect value.",
        max_steps=2,
    )

    second_messages = (
        fake.tool_requests[1][0]
    )

    assistant_message = (
        second_messages[-2]
    )

    tool_message = second_messages[-1]

    assert assistant_message.role == (
        "assistant"
    )

    assert assistant_message.tool_calls[
        0
    ].id == "call-1"

    assert tool_message.role == "tool"

    assert tool_message.tool_call_id == (
        "call-1"
    )

    assert '"success":true' in (
        tool_message.content
    )
    assert fake.tool_choices[1] == "none"


def test_agent_rejects_repeated_tool_call():
    repeated = decision_with_tool(
        call_id="call-1",
        value="TCP",
    )

    fake = FakeLLMClient(
        "{}",
        tool_decisions=[
            repeated,
            decision_with_tool(
                call_id="call-2",
                value="TCP",
            ),
        ],
    )

    runner = AgentRunner(
        llm_client=fake,
        registry=build_registry(),
    )

    with pytest.raises(
        AgentRepeatedToolCallError
    ):
        runner.run(
            user_request="Repeat forever.",
            max_steps=4,
        )


def test_reordered_json_keys_are_still_repeated():
    fake = FakeLLMClient(
        "{}",
        tool_decisions=[
            decision_with_tool(
                call_id="call-1",
                value="TCP",
                arguments_json=(
                    "{"
                    '"value":"TCP",'
                    '"label":"network"'
                    "}"
                ),
            ),
            decision_with_tool(
                call_id="call-2",
                value="TCP",
                arguments_json=(
                    "{"
                    '"label":"network",'
                    '"value":"TCP"'
                    "}"
                ),
            ),
        ],
    )

    runner = AgentRunner(
        llm_client=fake,
        registry=build_registry(),
    )

    with pytest.raises(
        AgentRepeatedToolCallError
    ):
        runner.run(
            user_request="Repeat with reordered keys.",
            max_steps=3,
        )


def test_different_get_note_ids_are_not_repeated():
    fake = FakeLLMClient(
        "{}",
        tool_decisions=[
            decision_with_get_note(
                call_id="call-1",
                note_id=1,
            ),
            decision_with_get_note(
                call_id="call-2",
                note_id=2,
            ),
            final_decision("Compared both notes."),
        ],
    )

    runner = AgentRunner(
        llm_client=fake,
        registry=build_get_note_registry(),
    )

    result = runner.run(
        user_request="Compare notes 1 and 2.",
        max_steps=3,
    )

    assert result.final_answer == (
        "Compared both notes."
    )
    assert len(fake.tool_requests) == 3
    assert fake.tool_choices == [
        "auto",
        "auto",
        "none",
    ]


def test_single_step_is_final_answer_only():
    fake = FakeLLMClient(
        "{}",
        tool_decisions=[
            final_decision("Final answer."),
        ],
    )

    runner = AgentRunner(
        llm_client=fake,
        registry=build_registry(),
    )

    result = runner.run(
        user_request="Answer directly.",
        max_steps=1,
    )

    assert result.final_answer == "Final answer."
    assert len(fake.tool_requests) == 1
    assert fake.tool_choices == ["none"]


def test_final_turn_rejects_tool_call():
    fake = FakeLLMClient(
        "{}",
        tool_decisions=[
            decision_with_tool(
                call_id="call-1",
                value="TCP",
            ),
        ],
    )

    runner = AgentRunner(
        llm_client=fake,
        registry=build_registry(),
    )

    with pytest.raises(
        LLMInvalidResponseError,
        match="final-answer-only",
    ):
        runner.run(
            user_request="Try to use a tool.",
            max_steps=1,
        )

    assert fake.tool_choices == ["none"]


def test_final_turn_rejects_empty_response():
    fake = FakeLLMClient(
        "{}",
        tool_decisions=[empty_decision()],
    )

    runner = AgentRunner(
        llm_client=fake,
        registry=build_registry(),
    )

    with pytest.raises(
        LLMInvalidResponseError,
        match="neither",
    ):
        runner.run(
            user_request="Return nothing.",
            max_steps=1,
        )


def test_agent_logs_safe_step_diagnostics(
    caplog,
):
    fake = FakeLLMClient(
        "{}",
        tool_decisions=[
            decision_with_tool(
                call_id="call-1",
                value="TCP",
            ),
            final_decision("Done."),
        ],
    )

    runner = AgentRunner(
        llm_client=fake,
        registry=build_registry(),
    )

    with caplog.at_level(
        "INFO",
        logger="uvicorn.error.agent",
    ):
        runner.run(
            user_request="private-user-content",
            max_steps=2,
        )

    log_text = caplog.text

    assert "agent_model_turn step=1" in log_text
    assert "agent_tool_result step=1" in log_text
    assert "agent_terminated reason=final_answer" in log_text
    assert "private-user-content" not in log_text
    assert '"value":"TCP"' not in log_text


def multiple_tool_decision() -> LLMToolDecision:
    return LLMToolDecision(
        content=None,
        tool_calls=(
            LLMToolCall(
                id="call-1",
                name="echo",
                arguments_json='{"value":"first"}',
            ),
            LLMToolCall(
                id="call-2",
                name="echo",
                arguments_json='{"value":"second"}',
            ),
        ),
        model="fake-model",
        usage=LLMUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
        duration_ms=5,
    )


def test_multiple_tools_execute_neither_before_correction():
    executions = []

    def echo(arguments: BaseModel):
        executions.append(arguments.value)
        return {"value": arguments.value}

    registry = ToolRegistry(
        [
            RegisteredTool(
                name="echo",
                description="Echo one value.",
                arguments_model=EchoArguments,
                handler=echo,
            )
        ]
    )
    fake = FakeLLMClient(
        "{}",
        tool_decisions=[
            multiple_tool_decision(),
            final_decision("Corrected answer."),
        ],
    )

    result = AgentRunner(
        llm_client=fake,
        registry=registry,
    ).run(
        user_request="Use at most one tool.",
        max_steps=2,
    )

    assert result.final_answer == "Corrected answer."
    assert executions == []
    assert result.usage.total_tokens == 30
    assert len(result.steps) == 1
    assert fake.content_contracts == [
        "final_answer_envelope",
        "final_answer_envelope",
    ]

    correction_messages = (
        fake.tool_requests[1][0]
    )
    assert all(
        "first" not in (message.content or "")
        and "second" not in (message.content or "")
        for message in correction_messages
    )


def test_repeated_multiple_tools_are_rejected_without_execution():
    executions = []

    def echo(arguments: BaseModel):
        executions.append(arguments.value)
        return {"value": arguments.value}

    registry = ToolRegistry(
        [
            RegisteredTool(
                name="echo",
                description="Echo one value.",
                arguments_model=EchoArguments,
                handler=echo,
            )
        ]
    )
    fake = FakeLLMClient(
        "{}",
        tool_decisions=[
            multiple_tool_decision(),
            multiple_tool_decision(),
        ],
    )

    with pytest.raises(
        ToolSelectionError,
        match="at most one",
    ):
        AgentRunner(
            llm_client=fake,
            registry=registry,
        ).run(
            user_request="Do not execute either.",
            max_steps=2,
        )

    assert executions == []


def test_adapter_protocol_error_is_corrected_once():
    fake = FakeLLMClient(
        "{}",
        tool_decisions=[
            LLMToolDecisionProtocolError(
                "invalid final answer envelope"
            ),
            final_decision("Recovered answer."),
        ],
    )

    result = AgentRunner(
        llm_client=fake,
        registry=build_registry(),
    ).run(
        user_request="Answer safely.",
        max_steps=2,
    )

    assert result.final_answer == "Recovered answer."
    assert len(fake.tool_requests) == 2


def test_parsed_dsml_answer_is_never_returned():
    executions = []

    def echo(arguments: BaseModel):
        executions.append(arguments.value)
        return {"value": arguments.value}

    registry = ToolRegistry(
        [
            RegisteredTool(
                name="echo",
                description="Echo one value.",
                arguments_model=EchoArguments,
                handler=echo,
            )
        ]
    )
    dsml = (
        "<｜｜DSML｜｜tool_calls>"
        '<｜｜DSML｜｜invoke name="echo">'
    )
    fake = FakeLLMClient(
        "{}",
        tool_decisions=[
            final_decision(dsml),
            final_decision(dsml),
        ],
    )

    with pytest.raises(
        LLMInvalidResponseError,
        match="reserved tool control marker",
    ):
        AgentRunner(
            llm_client=fake,
            registry=registry,
        ).run(
            user_request="Do not publish controls.",
            max_steps=2,
        )

    assert all(
        dsml not in (message.content or "")
        for message in fake.tool_requests[1][0]
    )
    assert executions == []

import json
import logging
from time import perf_counter

from app.agent.exceptions import (
    AgentMaxStepsExceededError,
    AgentRepeatedToolCallError,
)
from app.agent.models import (
    AgentRunResult,
    AgentStep,
)
from app.llm.client import LLMClient
from app.llm.agent_protocol import (
    contains_dsml_control_marker,
)
from app.llm.exceptions import (
    LLMInvalidResponseError,
    LLMToolDecisionProtocolError,
)
from app.llm.models import (
    LLMMessage,
    LLMToolCall,
    LLMUsage,
)
from app.prompts.agent import (
    build_agent_protocol_correction_message,
    build_agent_messages,
)
from app.tools.exceptions import (
    ToolSelectionError,
)
from app.tools.models import (
    ToolExecutionOutcome,
)
from app.tools.registry import ToolRegistry


MAX_AGENT_STEPS = 6
logger = logging.getLogger(
    "uvicorn.error.agent"
)


def _add_usage(
    current: LLMUsage,
    additional: LLMUsage,
) -> LLMUsage:
    return LLMUsage(
        prompt_tokens=(
            current.prompt_tokens
            + additional.prompt_tokens
        ),
        completion_tokens=(
            current.completion_tokens
            + additional.completion_tokens
        ),
        total_tokens=(
            current.total_tokens
            + additional.total_tokens
        ),
    )


def _tool_call_signature(
    tool_call: LLMToolCall,
) -> str:
    """Build a stable signature for loop detection."""

    try:
        arguments = json.loads(
            tool_call.arguments_json
        )

        normalized_arguments = json.dumps(
            arguments,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    except json.JSONDecodeError:
        normalized_arguments = (
            tool_call.arguments_json.strip()
        )

    return (
        f"{tool_call.name}:"
        f"{normalized_arguments}"
    )


def _serialize_tool_result(
    result: ToolExecutionOutcome,
) -> str:
    return json.dumps(
        {
            "success": result.success,
            "output": result.output,
            "error": result.error,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


class AgentRunner:
    """Run a bounded tool-using model loop."""

    def __init__(
        self,
        *,
        llm_client: LLMClient,
        registry: ToolRegistry,
    ) -> None:
        self._llm_client = llm_client
        self._registry = registry

    def run(
        self,
        *,
        user_request: str,
        max_steps: int,
        history_messages: list[
            LLMMessage
        ] | None = None,
        memory_summary: str | None = None,
    ) -> AgentRunResult:
        if not 1 <= max_steps <= MAX_AGENT_STEPS:
            raise ValueError(
                "max_steps must be between "
                f"1 and {MAX_AGENT_STEPS}"
            )

        self._llm_client.validate_configuration()

        messages = build_agent_messages(
            user_request=user_request,
            history_messages=tuple(
                history_messages or []
            ),
            memory_summary=memory_summary,
        )

        definitions = self._registry.definitions()

        steps: list[AgentStep] = []
        seen_tool_calls: set[str] = set()
        correction_used = False

        total_usage = LLMUsage()
        last_model = "unknown"

        started_at = perf_counter()

        for step_number in range(
            1,
            max_steps + 1,
        ):
            is_final_turn = (
                step_number == max_steps
            )
            tool_choice = (
                "none"
                if is_final_turn
                else "auto"
            )

            while True:
                try:
                    decision = (
                        self._llm_client.choose_tools(
                            messages=messages,
                            tools=definitions,
                            tool_choice=tool_choice,
                            content_contract=(
                                "final_answer_envelope"
                            ),
                        )
                    )
                except (
                    LLMToolDecisionProtocolError
                ) as error:
                    if correction_used:
                        logger.warning(
                            "agent_terminated reason="
                            "invalid_response "
                            "step=%d violation=%s",
                            step_number,
                            error.violation,
                        )
                        raise

                    correction_used = True
                    messages.append(
                        build_agent_protocol_correction_message(
                            violation=(
                                "it did not match the "
                                "required Agent response "
                                "protocol"
                            )
                        )
                    )
                    logger.warning(
                        "agent_protocol_correction "
                        "step=%d reason=invalid_response "
                        "violation=%s",
                        step_number,
                        error.violation,
                    )
                    continue

                last_model = decision.model

                total_usage = _add_usage(
                    total_usage,
                    decision.usage,
                )

                selected_tool = None

                if len(decision.tool_calls) == 1:
                    selected_tool = (
                        decision.tool_calls[0].name
                    )
                elif len(decision.tool_calls) > 1:
                    selected_tool = "multiple"

                logger.info(
                    "agent_model_turn step=%d "
                    "tool_choice=%s selected_tool=%s "
                    "model=%s duration_ms=%d "
                    "prompt_tokens=%d "
                    "completion_tokens=%d "
                    "total_tokens=%d",
                    step_number,
                    tool_choice,
                    selected_tool,
                    decision.model,
                    decision.duration_ms,
                    decision.usage.prompt_tokens,
                    decision.usage.completion_tokens,
                    decision.usage.total_tokens,
                )

                if (
                    decision.tool_calls
                    and decision.content is not None
                ):
                    if correction_used:
                        raise LLMInvalidResponseError(
                            "the Agent returned content "
                            "together with tool calls"
                        )

                    correction_used = True
                    messages.append(
                        build_agent_protocol_correction_message(
                            violation=(
                                "it mixed ordinary content "
                                "with native tool calls"
                            )
                        )
                    )
                    logger.warning(
                        "agent_protocol_correction "
                        "step=%d reason=mixed_content",
                        step_number,
                    )
                    continue

                if len(decision.tool_calls) > 1:
                    if correction_used:
                        raise ToolSelectionError(
                            "the Agent supports at most "
                            "one tool call per step"
                        )

                    correction_used = True
                    messages.append(
                        build_agent_protocol_correction_message(
                            violation=(
                                "it returned more than one "
                                "native tool call"
                            )
                        )
                    )
                    logger.warning(
                        "agent_protocol_correction "
                        "step=%d reason=multiple_tools",
                        step_number,
                    )
                    continue

                if (
                    not decision.tool_calls
                    and decision.content is not None
                    and contains_dsml_control_marker(
                        decision.content
                    )
                ):
                    if correction_used:
                        raise LLMInvalidResponseError(
                            "the Agent final answer "
                            "contained a reserved tool "
                            "control marker"
                        )

                    correction_used = True
                    messages.append(
                        build_agent_protocol_correction_message(
                            violation=(
                                "its answer contained a "
                                "reserved tool-control "
                                "marker"
                            )
                        )
                    )
                    logger.warning(
                        "agent_protocol_correction "
                        "step=%d reason=control_marker",
                        step_number,
                    )
                    continue

                break

            if (
                is_final_turn
                and decision.tool_calls
            ):
                logger.warning(
                    "agent_terminated reason="
                    "tool_call_on_final_turn "
                    "step=%d selected_tool=%s",
                    step_number,
                    selected_tool,
                )

                raise LLMInvalidResponseError(
                    "the Agent attempted a tool call "
                    "during the final-answer-only turn"
                )

            # No tool means the model has completed.
            if not decision.tool_calls:
                if decision.content is None:
                    logger.warning(
                        "agent_terminated reason="
                        "empty_final_response step=%d",
                        step_number,
                    )

                    raise LLMInvalidResponseError(
                        "the Agent returned neither "
                        "a tool call nor a final answer"
                    )

                steps.append(
                    AgentStep(
                        step_number=step_number,
                        assistant_text=(
                            decision.content
                        ),
                        tool_call=None,
                        tool_result=None,
                        model=decision.model,
                        usage=decision.usage,
                        duration_ms=(
                            decision.duration_ms
                        ),
                    )
                )

                total_duration_ms = int(
                    (
                        perf_counter()
                        - started_at
                    )
                    * 1000
                )

                logger.info(
                    "agent_terminated reason="
                    "final_answer step=%d "
                    "duration_ms=%d total_tokens=%d",
                    step_number,
                    total_duration_ms,
                    total_usage.total_tokens,
                )

                return AgentRunResult(
                    final_answer=decision.content,
                    steps=tuple(steps),
                    model=last_model,
                    usage=total_usage,
                    duration_ms=(
                        total_duration_ms
                    ),
                )

            tool_call = decision.tool_calls[0]

            signature = _tool_call_signature(
                tool_call
            )

            if signature in seen_tool_calls:
                logger.warning(
                    "agent_terminated reason="
                    "repeated_tool_call step=%d "
                    "selected_tool=%s",
                    step_number,
                    tool_call.name,
                )

                raise AgentRepeatedToolCallError(
                    "the Agent repeated the same "
                    f"tool call: {tool_call.name}"
                )

            seen_tool_calls.add(signature)

            tool_result = self._registry.execute(
                tool_call
            )

            logger.info(
                "agent_tool_result step=%d tool=%s "
                "argument_keys=%s success=%s",
                step_number,
                tool_call.name,
                ",".join(
                    sorted(
                        str(key)
                        for key
                        in tool_result.arguments
                    )
                ),
                tool_result.success,
            )

            steps.append(
                AgentStep(
                    step_number=step_number,
                    assistant_text=(
                        decision.content
                    ),
                    tool_call=tool_call,
                    tool_result=tool_result,
                    model=decision.model,
                    usage=decision.usage,
                    duration_ms=(
                        decision.duration_ms
                    ),
                )
            )

            # Reconstruct the assistant tool-call message.
            messages.append(
                LLMMessage(
                    role="assistant",
                    content=decision.content,
                    tool_calls=(tool_call,),
                )
            )

            # Return the actual tool result to the model.
            messages.append(
                LLMMessage(
                    role="tool",
                    content=(
                        _serialize_tool_result(
                            tool_result
                        )
                    ),
                    tool_call_id=tool_call.id,
                )
            )

        logger.warning(
            "agent_terminated reason=max_steps "
            "steps_completed=%d",
            max_steps,
        )

        raise AgentMaxStepsExceededError(
            "the Agent reached the maximum "
            f"of {max_steps} steps without "
            "producing a final answer"
        )

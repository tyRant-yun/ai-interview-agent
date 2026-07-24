import json

from fastapi import APIRouter

from app.agent.models import AgentStep
from app.api.agent_schemas import (
    AgentRunRequest,
    AgentRunResponse,
    AgentStepResponse,
)
from app.api.dependencies import (
    AgentRunnerDependency,
)
from app.api.interview_schemas import (
    LLMUsageResponse,
)
from app.api.tool_schemas import (
    ToolCallResponse,
    ToolResultResponse,
)


router = APIRouter(
    prefix="/agent",
    tags=["agent"],
)


def _serialize_step(
    step: AgentStep,
) -> AgentStepResponse:
    tool_call_response = None

    if step.tool_call is not None:
        tool_call_response = ToolCallResponse(
            id=step.tool_call.id,
            name=step.tool_call.name,
            arguments=json.loads(
                step.tool_call.arguments_json
            ),
        )

    tool_result_response = None

    if step.tool_result is not None:
        tool_result_response = (
            ToolResultResponse(
                call_id=(
                    step.tool_result.call_id
                ),
                tool_name=(
                    step.tool_result.tool_name
                ),
                success=(
                    step.tool_result.success
                ),
                output=(
                    step.tool_result.output
                ),
                error=(
                    step.tool_result.error
                ),
            )
        )

    return AgentStepResponse(
        step_number=step.step_number,
        assistant_text=step.assistant_text,
        tool_call=tool_call_response,
        tool_result=tool_result_response,
        model=step.model,
        usage=(
            LLMUsageResponse.model_validate(
                step.usage
            )
        ),
        duration_ms=step.duration_ms,
    )


@router.post(
    "/run",
    response_model=AgentRunResponse,
)
def run_agent(
    payload: AgentRunRequest,
    runner: AgentRunnerDependency,
) -> AgentRunResponse:
    result = runner.run(
        user_request=payload.user_request,
        max_steps=payload.max_steps,
    )

    steps = [
        _serialize_step(step)
        for step in result.steps
    ]

    return AgentRunResponse(
        final_answer=result.final_answer,
        steps=steps,
        step_count=len(steps),
        model=result.model,
        usage=(
            LLMUsageResponse.model_validate(
                result.usage
            )
        ),
        duration_ms=result.duration_ms,
    )

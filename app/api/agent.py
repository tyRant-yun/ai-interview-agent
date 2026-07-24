from fastapi import APIRouter

from app.api.agent_serialization import (
    serialize_agent_step,
)
from app.api.agent_schemas import (
    AgentRunRequest,
    AgentRunResponse,
)
from app.api.dependencies import (
    AgentRunnerDependency,
)
from app.api.interview_schemas import (
    LLMUsageResponse,
)


router = APIRouter(
    prefix="/agent",
    tags=["agent"],
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
        serialize_agent_step(step)
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

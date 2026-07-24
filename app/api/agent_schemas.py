from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.api.interview_schemas import (
    LLMUsageResponse,
)
from app.api.tool_schemas import (
    ToolCallResponse,
    ToolResultResponse,
)


class AgentRunRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    user_request: str = Field(
        min_length=1,
        max_length=4000,
    )

    max_steps: int = Field(
        default=4,
        ge=1,
        le=6,
    )


class AgentStepResponse(BaseModel):
    step_number: int
    assistant_text: str | None
    tool_call: ToolCallResponse | None
    tool_result: ToolResultResponse | None
    model: str
    usage: LLMUsageResponse
    duration_ms: int


class AgentRunResponse(BaseModel):
    final_answer: str
    steps: list[AgentStepResponse]
    step_count: int
    model: str
    usage: LLMUsageResponse
    duration_ms: int

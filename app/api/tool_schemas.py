from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.api.interview_schemas import (
    LLMUsageResponse,
)


class ToolCallingRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    user_request: str = Field(
        min_length=1,
        max_length=2000,
    )


class ToolCallResponse(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]


class ToolResultResponse(BaseModel):
    call_id: str
    tool_name: str
    success: bool
    output: Any = None
    error: str | None = None


class ToolCallingResponse(BaseModel):
    assistant_text: str | None
    tool_call: ToolCallResponse | None
    tool_result: ToolResultResponse | None
    model: str
    usage: LLMUsageResponse
    duration_ms: int

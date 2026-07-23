import json

from fastapi import APIRouter

from app.api.dependencies import (
    ToolCallingServiceDependency,
)
from app.api.interview_schemas import LLMUsageResponse
from app.api.tool_schemas import (
    ToolCallResponse,
    ToolCallingRequest,
    ToolCallingResponse,
    ToolResultResponse,
)


router = APIRouter(
    prefix="/tools",
    tags=["tools"],
)


@router.post(
    "/execute",
    response_model=ToolCallingResponse,
)
def execute_selected_tool(
    payload: ToolCallingRequest,
    service: ToolCallingServiceDependency,
) -> ToolCallingResponse:
    result = service.resolve_and_execute(
        user_request=payload.user_request
    )

    tool_call_response = None

    if result.tool_call is not None:
        tool_call_response = ToolCallResponse(
            id=result.tool_call.id,
            name=result.tool_call.name,
            arguments=json.loads(
                result.tool_call.arguments_json
            ),
        )

    tool_result_response = None

    if result.tool_result is not None:
        tool_result_response = (
            ToolResultResponse(
                call_id=(
                    result.tool_result.call_id
                ),
                tool_name=(
                    result.tool_result.tool_name
                ),
                success=(
                    result.tool_result.success
                ),
                output=(
                    result.tool_result.output
                ),
                error=(
                    result.tool_result.error
                ),
            )
        )

    return ToolCallingResponse(
        assistant_text=result.assistant_text,
        tool_call=tool_call_response,
        tool_result=tool_result_response,
        model=result.model,
        usage=(
            LLMUsageResponse.model_validate(
                result.usage
            )
        ),
        duration_ms=result.duration_ms,
    )

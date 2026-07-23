from collections.abc import AsyncIterator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.api.dependencies import (
    QuestionGenerationServiceDependency,
)
from app.api.interview_schemas import (
    GenerateQuestionsRequest,
    QuestionGenerationResponse,
    QuestionStreamCompletedResponse,
    QuestionStreamDeltaResponse,
    QuestionStreamErrorResponse,
    QuestionStreamStartedResponse,
)
from app.api.sse import encode_sse
from app.domain.interview import (
    QuestionStreamCompleted,
    QuestionStreamDelta,
    QuestionStreamStarted,
)
from app.llm.exceptions import (
    LLMInvalidResponseError,
    LLMTimeoutError,
    LLMUpstreamError,
)


router = APIRouter(
    prefix="/interview",
    tags=["interview"],
)


@router.post(
    "/questions",
    response_model=QuestionGenerationResponse,
)
def generate_questions(
    payload: GenerateQuestionsRequest,
    service: QuestionGenerationServiceDependency,
) -> QuestionGenerationResponse:
    result = service.generate_questions(
        note_id=payload.note_id,
        difficulty=payload.difficulty,
        question_count=payload.question_count,
    )

    return QuestionGenerationResponse.model_validate(
        result
    )


@router.post(
    "/questions/stream",
    response_class=StreamingResponse,
)
async def stream_questions(
    payload: GenerateQuestionsRequest,
    request: Request,
    service: QuestionGenerationServiceDependency,
) -> StreamingResponse:
    # 404 and 503 still happen before the HTTP stream begins.
    prepared = service.prepare_questions(
        note_id=payload.note_id,
        difficulty=payload.difficulty,
        question_count=payload.question_count,
    )

    async def event_generator() -> AsyncIterator[str]:
        try:
            async for update in service.stream_questions(
                prepared=prepared
            ):
                if await request.is_disconnected():
                    return

                if isinstance(
                    update,
                    QuestionStreamStarted,
                ):
                    body = (
                        QuestionStreamStartedResponse
                        .model_validate(update)
                    )

                    yield encode_sse(
                        event="started",
                        data=body,
                    )

                elif isinstance(
                    update,
                    QuestionStreamDelta,
                ):
                    body = (
                        QuestionStreamDeltaResponse
                        .model_validate(update)
                    )

                    yield encode_sse(
                        event="delta",
                        data=body,
                    )

                elif isinstance(
                    update,
                    QuestionStreamCompleted,
                ):
                    body = (
                        QuestionStreamCompletedResponse
                        .model_validate(update)
                    )

                    yield encode_sse(
                        event="completed",
                        data=body,
                    )

        except LLMTimeoutError as error:
            yield encode_sse(
                event="error",
                data=QuestionStreamErrorResponse(
                    error="llm_timeout",
                    detail=str(error),
                ),
            )

        except LLMUpstreamError as error:
            yield encode_sse(
                event="error",
                data=QuestionStreamErrorResponse(
                    error="llm_upstream_error",
                    detail=str(error),
                ),
            )

        except LLMInvalidResponseError as error:
            yield encode_sse(
                event="error",
                data=QuestionStreamErrorResponse(
                    error="llm_invalid_response",
                    detail=str(error),
                ),
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.interview import router as interview_router
from app.api.notes import router as notes_router
from app.db.init_db import create_db_and_tables
from app.domain.exceptions import (
    DuplicateNoteError,
    NoteNotFoundError,
)
from app.llm.exceptions import (
    LLMInvalidResponseError,
    LLMNotConfiguredError,
    LLMTimeoutError,
    LLMUpstreamError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="AI Interview Learning Agent",
    description=(
        "Backend API for managing interview-preparation "
        "notes and AI-generated interview questions."
    ),
    version="0.3.0",
    lifespan=lifespan,
)


@app.get(
    "/health",
    tags=["system"],
)
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(NoteNotFoundError)
async def handle_note_not_found(
    request: Request,
    error: NoteNotFoundError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "note_not_found",
            "detail": str(error),
        },
    )


@app.exception_handler(DuplicateNoteError)
async def handle_duplicate_note(
    request: Request,
    error: DuplicateNoteError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "duplicate_note",
            "detail": str(error),
        },
    )


@app.exception_handler(LLMNotConfiguredError)
async def handle_llm_not_configured(
    request: Request,
    error: LLMNotConfiguredError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "llm_not_configured",
            "detail": str(error),
        },
    )


@app.exception_handler(LLMTimeoutError)
async def handle_llm_timeout(
    request: Request,
    error: LLMTimeoutError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
        content={
            "error": "llm_timeout",
            "detail": str(error),
        },
    )


@app.exception_handler(LLMUpstreamError)
async def handle_llm_upstream_error(
    request: Request,
    error: LLMUpstreamError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "error": "llm_upstream_error",
            "detail": str(error),
        },
    )


@app.exception_handler(LLMInvalidResponseError)
async def handle_invalid_llm_response(
    request: Request,
    error: LLMInvalidResponseError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "error": "llm_invalid_response",
            "detail": str(error),
        },
    )


app.include_router(notes_router)
app.include_router(interview_router)

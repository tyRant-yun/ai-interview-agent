from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.notes import router as notes_router
from app.db.init_db import create_db_and_tables
from app.domain.exceptions import (
    DuplicateNoteError,
    NoteNotFoundError,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(
    title="AI Interview Learning Agent",
    description=(
        "Backend API for managing interview-preparation "
        "notes and future AI learning workflows."
    ),
    version="0.2.0",
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


app.include_router(notes_router)

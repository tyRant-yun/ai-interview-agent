from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.settings import Settings, get_settings
from app.db.session import get_session
from app.domain.note_manager import NoteManager
from app.llm.client import OpenAICompatibleLLMClient
from app.repositories.sqlalchemy_note_repository import (
    SQLAlchemyNoteRepository,
)
from app.services.question_generation import (
    QuestionGenerationService,
)


def get_note_manager(
    session: Session = Depends(get_session),
) -> NoteManager:
    repository = SQLAlchemyNoteRepository(session)
    return NoteManager(repository)


NoteManagerDependency = Annotated[
    NoteManager,
    Depends(get_note_manager),
]


def get_llm_client(
    settings: Settings = Depends(get_settings),
) -> OpenAICompatibleLLMClient:
    return OpenAICompatibleLLMClient(
        base_url=settings.llm_api_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        stream_include_usage=(
            settings.llm_stream_include_usage
        ),
    )


LLMClientDependency = Annotated[
    OpenAICompatibleLLMClient,
    Depends(get_llm_client),
]


def get_question_generation_service(
    manager: NoteManagerDependency,
    llm_client: LLMClientDependency,
) -> QuestionGenerationService:
    return QuestionGenerationService(
        note_manager=manager,
        llm_client=llm_client,
    )


QuestionGenerationServiceDependency = Annotated[
    QuestionGenerationService,
    Depends(get_question_generation_service),
]

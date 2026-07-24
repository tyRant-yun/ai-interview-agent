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
from app.services.tool_calling import (
    ToolCallingService,
)
from app.tools.note_tools import (
    build_note_tools,
)
from app.tools.registry import ToolRegistry
from app.services.agent_runner import (
    AgentRunner,
)
from app.domain.conversation_manager import (
    ConversationManager,
)
from app.repositories.sqlalchemy_conversation_repository import (
    SQLAlchemyConversationRepository,
)
from app.services.conversation_agent import (
    ConversationAgentService,
)
from app.services.conversation_memory import (
    ConversationMemoryService,
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

def get_conversation_manager(
    session: Session = Depends(get_session),
) -> ConversationManager:
    repository = (
        SQLAlchemyConversationRepository(
            session
        )
    )

    return ConversationManager(
        repository
    )


ConversationManagerDependency = Annotated[
    ConversationManager,
    Depends(get_conversation_manager),
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

def get_tool_registry(
    manager: NoteManagerDependency,
) -> ToolRegistry:
    return ToolRegistry(
        build_note_tools(manager)
    )


ToolRegistryDependency = Annotated[
    ToolRegistry,
    Depends(get_tool_registry),
]


def get_tool_calling_service(
    llm_client: LLMClientDependency,
    registry: ToolRegistryDependency,
) -> ToolCallingService:
    return ToolCallingService(
        llm_client=llm_client,
        registry=registry,
    )


ToolCallingServiceDependency = Annotated[
    ToolCallingService,
    Depends(get_tool_calling_service),
]

def get_agent_runner(
    llm_client: LLMClientDependency,
    registry: ToolRegistryDependency,
) -> AgentRunner:
    return AgentRunner(
        llm_client=llm_client,
        registry=registry,
    )


AgentRunnerDependency = Annotated[
    AgentRunner,
    Depends(get_agent_runner),
]

def get_conversation_memory_service(
    manager: ConversationManagerDependency,
    llm_client: LLMClientDependency,
    settings: Settings = Depends(
        get_settings
    ),
) -> ConversationMemoryService:
    return ConversationMemoryService(
        manager=manager,
        llm_client=llm_client,
        recent_message_limit=(
            settings
            .conversation_recent_message_limit
        ),
        summary_trigger_messages=(
            settings
            .conversation_summary_trigger_messages
        ),
        context_char_budget=(
            settings
            .conversation_context_char_budget
        ),
    )


ConversationMemoryServiceDependency = Annotated[
    ConversationMemoryService,
    Depends(
        get_conversation_memory_service
    ),
]


def get_conversation_agent_service(
    runner: AgentRunnerDependency,
    memory: ConversationMemoryServiceDependency,
) -> ConversationAgentService:
    return ConversationAgentService(
        runner=runner,
        memory=memory,
    )


ConversationAgentServiceDependency = Annotated[
    ConversationAgentService,
    Depends(
        get_conversation_agent_service
    ),
]

from fastapi import (
    APIRouter,
    status,
)

from app.api.agent_schemas import (
    AgentRunRequest,
)
from app.api.agent_serialization import (
    serialize_agent_step,
)
from app.api.conversation_schemas import (
    ConversationAgentRunResponse,
    ConversationCreateRequest,
    ConversationMemoryResponse,
    ConversationMessageResponse,
    ConversationResponse,
    MemoryCompactionResponse,
)
from app.api.dependencies import (
    ConversationAgentServiceDependency,
    ConversationManagerDependency,
)
from app.api.interview_schemas import (
    LLMUsageResponse,
)


router = APIRouter(
    prefix="/conversations",
    tags=["conversations"],
)


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_conversation(
    payload: ConversationCreateRequest,
    manager: ConversationManagerDependency,
) -> ConversationResponse:
    conversation = (
        manager.create_conversation(
            title=payload.title
        )
    )

    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        summary=conversation.summary,
        summarized_through_message_id=(
            conversation
            .summarized_through_message_id
        ),
        messages=[],
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
def get_conversation(
    conversation_id: int,
    manager: ConversationManagerDependency,
) -> ConversationResponse:
    conversation = (
        manager.get_conversation(
            conversation_id
        )
    )

    messages = manager.list_messages(
        conversation_id
    )

    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        summary=conversation.summary,
        summarized_through_message_id=(
            conversation
            .summarized_through_message_id
        ),
        messages=[
            ConversationMessageResponse(
                id=message.id,
                role=message.role,
                content=message.content,
            )
            for message in messages
        ],
    )


@router.post(
    "/{conversation_id}/agent",
    response_model=(
        ConversationAgentRunResponse
    ),
)
def run_conversation_agent(
    conversation_id: int,
    payload: AgentRunRequest,
    service: ConversationAgentServiceDependency,
) -> ConversationAgentRunResponse:
    result = service.run(
        conversation_id=conversation_id,
        user_request=payload.user_request,
        max_steps=payload.max_steps,
    )

    agent_result = result.agent_result

    summary_usage = None

    if result.compaction.usage is not None:
        summary_usage = (
            LLMUsageResponse.model_validate(
                result.compaction.usage
            )
        )

    return ConversationAgentRunResponse(
        conversation_id=conversation_id,
        final_answer=(
            agent_result.final_answer
        ),
        steps=[
            serialize_agent_step(step)
            for step in agent_result.steps
        ],
        step_count=len(
            agent_result.steps
        ),
        model=agent_result.model,
        usage=(
            LLMUsageResponse.model_validate(
                agent_result.usage
            )
        ),
        duration_ms=(
            agent_result.duration_ms
        ),
        memory=ConversationMemoryResponse(
            history_messages_used=(
                result
                .history_messages_used
            ),
            summary_used=(
                result.summary_used
            ),
            context_truncated=(
                result.context_truncated
            ),
            compaction=(
                MemoryCompactionResponse(
                    status=(
                        result
                        .compaction.status
                    ),
                    messages_summarized=(
                        result
                        .compaction
                        .messages_summarized
                    ),
                    summary_usage=(
                        summary_usage
                    ),
                    summary_duration_ms=(
                        result
                        .compaction.duration_ms
                    ),
                )
            ),
        ),
    )

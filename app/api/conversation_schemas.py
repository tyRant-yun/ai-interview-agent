from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.api.agent_schemas import (
    AgentRunResponse,
)
from app.api.interview_schemas import (
    LLMUsageResponse,
)
from app.domain.conversation import (
    ConversationRole,
)


class ConversationCreateRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )


class ConversationMessageResponse(BaseModel):
    id: int
    role: ConversationRole
    content: str


class ConversationResponse(BaseModel):
    id: int
    title: str | None
    summary: str | None
    summarized_through_message_id: int | None
    messages: list[
        ConversationMessageResponse
    ]


class MemoryCompactionResponse(BaseModel):
    status: str
    messages_summarized: int
    summary_usage: LLMUsageResponse | None
    summary_duration_ms: int | None


class ConversationMemoryResponse(BaseModel):
    history_messages_used: int
    summary_used: bool
    context_truncated: bool
    compaction: MemoryCompactionResponse


class ConversationAgentRunResponse(
    AgentRunResponse
):
    conversation_id: int
    memory: ConversationMemoryResponse

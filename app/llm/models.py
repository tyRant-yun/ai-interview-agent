from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class LLMMessage:
    """One message sent to a chat-completion model."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class LLMUsage:
    """Token usage returned by the upstream model."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass(frozen=True, slots=True)
class LLMResult:
    """Normalized result returned by an LLM client."""

    content: str
    model: str
    usage: LLMUsage
    duration_ms: int


@dataclass(frozen=True, slots=True)
class LLMStreamChunk:
    """One normalized chunk from a streaming model response."""

    delta: str = ""
    model: str | None = None
    usage: LLMUsage | None = None
    finish_reason: str | None = None

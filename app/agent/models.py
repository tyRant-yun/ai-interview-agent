from dataclasses import dataclass

from app.llm.models import (
    LLMToolCall,
    LLMUsage,
)
from app.tools.models import (
    ToolExecutionOutcome,
)


@dataclass(frozen=True, slots=True)
class AgentStep:
    """One observable Agent model turn."""

    step_number: int
    assistant_text: str | None
    tool_call: LLMToolCall | None
    tool_result: ToolExecutionOutcome | None
    model: str
    usage: LLMUsage
    duration_ms: int


@dataclass(frozen=True, slots=True)
class AgentRunResult:
    """Completed result of one controlled Agent run."""

    final_answer: str
    steps: tuple[AgentStep, ...]
    model: str
    usage: LLMUsage
    duration_ms: int

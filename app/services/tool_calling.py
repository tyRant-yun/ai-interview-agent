from dataclasses import dataclass
from typing import Any

from app.llm.client import LLMClient
from app.llm.models import (
    LLMToolCall,
    LLMUsage,
)
from app.prompts.tool_selection import (
    build_tool_selection_messages,
)
from app.tools.exceptions import (
    ToolSelectionError,
)
from app.tools.models import (
    ToolExecutionOutcome,
)
from app.tools.registry import ToolRegistry


@dataclass(frozen=True, slots=True)
class ToolCallingResult:
    assistant_text: str | None
    tool_call: LLMToolCall | None
    tool_result: ToolExecutionOutcome | None
    model: str
    usage: LLMUsage
    duration_ms: int


class ToolCallingService:
    """Select and execute at most one backend tool."""

    def __init__(
        self,
        *,
        llm_client: LLMClient,
        registry: ToolRegistry,
    ) -> None:
        self._llm_client = llm_client
        self._registry = registry

    def resolve_and_execute(
        self,
        *,
        user_request: str,
    ) -> ToolCallingResult:
        messages = (
            build_tool_selection_messages(
                user_request=user_request
            )
        )

        decision = (
            self._llm_client.choose_tools(
                messages=messages,
                tools=(
                    self._registry
                    .definitions()
                ),
            )
        )

        if len(decision.tool_calls) > 1:
            raise ToolSelectionError(
                "Day 8 supports at most "
                "one tool call"
            )

        if not decision.tool_calls:
            return ToolCallingResult(
                assistant_text=decision.content,
                tool_call=None,
                tool_result=None,
                model=decision.model,
                usage=decision.usage,
                duration_ms=decision.duration_ms,
            )

        tool_call = decision.tool_calls[0]

        tool_result = self._registry.execute(
            tool_call
        )

        return ToolCallingResult(
            assistant_text=decision.content,
            tool_call=tool_call,
            tool_result=tool_result,
            model=decision.model,
            usage=decision.usage,
            duration_ms=decision.duration_ms,
        )

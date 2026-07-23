from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ToolExecutionOutcome:
    """Result of one validated backend tool execution."""

    call_id: str
    tool_name: str
    arguments: dict[str, Any]
    success: bool
    output: Any = None
    error: str | None = None

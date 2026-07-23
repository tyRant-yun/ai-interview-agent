import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from app.domain.exceptions import NoteError
from app.llm.models import (
    LLMToolCall,
    LLMToolDefinition,
)
from app.tools.exceptions import (
    ToolArgumentsError,
    ToolNotRegisteredError,
)
from app.tools.models import ToolExecutionOutcome


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    """One backend function exposed through Tool Calling."""

    name: str
    description: str
    arguments_model: type[BaseModel]
    handler: Callable[[BaseModel], Any]

    def to_llm_definition(
        self,
    ) -> LLMToolDefinition:
        return LLMToolDefinition(
            name=self.name,
            description=self.description,
            parameters=(
                self.arguments_model
                .model_json_schema()
            ),
        )


class ToolRegistry:
    """Whitelist and execute application tools."""

    def __init__(
        self,
        tools: list[RegisteredTool],
    ) -> None:
        self._tools = {
            tool.name: tool
            for tool in tools
        }

        if len(self._tools) != len(tools):
            raise ValueError(
                "tool names must be unique"
            )

    def definitions(
        self,
    ) -> list[LLMToolDefinition]:
        return [
            tool.to_llm_definition()
            for tool in self._tools.values()
        ]

    def execute(
        self,
        tool_call: LLMToolCall,
    ) -> ToolExecutionOutcome:
        tool = self._tools.get(
            tool_call.name
        )

        if tool is None:
            raise ToolNotRegisteredError(
                f"tool {tool_call.name!r} "
                "is not registered"
            )

        try:
            raw_arguments = json.loads(
                tool_call.arguments_json
            )

            if not isinstance(
                raw_arguments,
                dict,
            ):
                raise TypeError(
                    "tool arguments must be an object"
                )

            validated_arguments = (
                tool.arguments_model
                .model_validate(raw_arguments)
            )

        except (
            json.JSONDecodeError,
            TypeError,
            ValidationError,
        ) as error:
            raise ToolArgumentsError(
                f"invalid arguments for "
                f"tool {tool.name!r}"
            ) from error

        try:
            output = tool.handler(
                validated_arguments
            )

        except NoteError as error:
            return ToolExecutionOutcome(
                call_id=tool_call.id,
                tool_name=tool.name,
                arguments=raw_arguments,
                success=False,
                error=str(error),
            )

        return ToolExecutionOutcome(
            call_id=tool_call.id,
            tool_name=tool.name,
            arguments=raw_arguments,
            success=True,
            output=output,
        )

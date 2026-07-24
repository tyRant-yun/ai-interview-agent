from collections.abc import AsyncIterator
from typing import Literal

from app.llm.exceptions import LLMError
from app.llm.agent_protocol import (
    ToolContentContract,
)
from app.llm.models import (
    LLMMessage,
    LLMResult,
    LLMStreamChunk,
    LLMToolDecision,
    LLMToolDefinition,
    LLMUsage,
)


class FakeLLMClient:
    """Controllable LLM client for deterministic tests."""

    def __init__(
        self,
        content: str,
        *,
        config_error: LLMError | None = None,
        generate_error: LLMError | None = None,
        stream_error: LLMError | None = None,
        tool_decision: LLMToolDecision | None = None,
        tool_decisions: list[
            LLMToolDecision | LLMError
        ] | None = None,
    ) -> None:
        if (
            tool_decision is not None
            and tool_decisions is not None
        ):
            raise ValueError(
                "configure tool_decision or "
                "tool_decisions, not both"
            )
        self._content = content
        self._config_error = config_error
        self._generate_error = generate_error
        self._stream_error = stream_error
        self._tool_decision = tool_decision
        self._tool_decisions = (
            list(tool_decisions)
            if tool_decisions is not None
            else None
        )
        self.tool_requests: list[
            tuple[
                tuple[LLMMessage, ...],
                tuple[LLMToolDefinition, ...],
            ]
        ] = []
        self.tool_choices: list[
            Literal["auto", "none"]
        ] = []
        self.content_contracts: list[
            ToolContentContract
        ] = []

    def validate_configuration(self) -> None:
        if self._config_error is not None:
            raise self._config_error

    def generate_json(
        self,
        *,
        messages: list[LLMMessage],
    ) -> LLMResult:
        if self._generate_error is not None:
            raise self._generate_error

        return LLMResult(
            content=self._content,
            model="fake-model",
            usage=LLMUsage(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
            ),
            duration_ms=12,
        )

    async def stream_content(
        self,
        *,
        messages: list[LLMMessage],
    ) -> AsyncIterator[LLMStreamChunk]:
        midpoint = max(
            1,
            len(self._content) // 2,
        )

        first_part = self._content[:midpoint]
        second_part = self._content[midpoint:]

        if first_part:
            yield LLMStreamChunk(
                delta=first_part,
                model="fake-model",
            )

        # Simulate a stream that fails after partial output.
        if self._stream_error is not None:
            raise self._stream_error

        if second_part:
            yield LLMStreamChunk(
                delta=second_part,
                model="fake-model",
            )

        yield LLMStreamChunk(
            model="fake-model",
            usage=LLMUsage(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
            ),
            finish_reason="stop",
        )

    def choose_tools(
        self,
        *,
        messages: list[LLMMessage],
        tools: list[LLMToolDefinition],
        tool_choice: Literal["auto", "none"] = "auto",
        content_contract: ToolContentContract = "plain_text",
    ) -> LLMToolDecision:
        if self._config_error is not None:
            raise self._config_error

        self.tool_requests.append(
            (
                tuple(messages),
                tuple(tools),
            )
        )
        self.tool_choices.append(tool_choice)
        self.content_contracts.append(
            content_contract
        )

        if self._tool_decisions is not None:
            if not self._tool_decisions:
                raise AssertionError(
                    "no fake tool decisions remain"
                )

            result = self._tool_decisions.pop(0)

            if isinstance(result, LLMError):
                raise result

            return result

        if self._tool_decision is None:
            raise AssertionError(
                "tool decision must be configured "
                "before choose_tools is called"
            )

        return self._tool_decision

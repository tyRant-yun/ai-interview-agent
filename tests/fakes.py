from collections.abc import AsyncIterator

from app.llm.exceptions import LLMError
from app.llm.models import (
    LLMMessage,
    LLMResult,
    LLMStreamChunk,
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
    ) -> None:
        self._content = content
        self._config_error = config_error
        self._generate_error = generate_error
        self._stream_error = stream_error

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

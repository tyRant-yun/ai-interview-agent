from time import perf_counter
from typing import Protocol

import httpx

from app.llm.exceptions import (
    LLMInvalidResponseError,
    LLMNotConfiguredError,
    LLMTimeoutError,
    LLMUpstreamError,
)
from app.llm.models import (
    LLMMessage,
    LLMResult,
    LLMUsage,
)


class LLMClient(Protocol):
    """Contract required by AI application services."""

    def generate_json(
        self,
        *,
        messages: list[LLMMessage],
    ) -> LLMResult:
        ...


class OpenAICompatibleLLMClient:
    """Synchronous client for an OpenAI-compatible chat endpoint."""

    def __init__(
        self,
        *,
        base_url: str | None,
        api_key: str | None,
        model: str | None,
        timeout_seconds: float,
    ) -> None:
        self._base_url = base_url.rstrip("/") if base_url else None
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    def generate_json(
        self,
        *,
        messages: list[LLMMessage],
    ) -> LLMResult:
        self._ensure_configured()

        endpoint = f"{self._base_url}/chat/completions"

        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in messages
            ],
            "temperature": 0.2,
            "response_format": {
                "type": "json_object",
            },
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        started_at = perf_counter()

        try:
            with httpx.Client(
                timeout=self._timeout_seconds
            ) as client:
                response = client.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                )

                response.raise_for_status()

        except httpx.TimeoutException as error:
            raise LLMTimeoutError(
                "the model request timed out"
            ) from error

        except httpx.HTTPStatusError as error:
            body = error.response.text[:500]

            raise LLMUpstreamError(
                "the model service returned "
                f"HTTP {error.response.status_code}: {body}"
            ) from error

        except httpx.HTTPError as error:
            raise LLMUpstreamError(
                f"failed to reach the model service: {error}"
            ) from error

        duration_ms = int(
            (perf_counter() - started_at) * 1000
        )

        try:
            data = response.json()

            content = data["choices"][0]["message"]["content"]

            if not isinstance(content, str):
                raise TypeError(
                    "message content is not a string"
                )

            content = content.strip()

            if not content:
                raise ValueError(
                    "message content is empty"
                )

        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as error:
            raise LLMInvalidResponseError(
                "the model response did not contain "
                "a valid assistant message"
            ) from error

        usage_data = data.get("usage") or {}

        usage = LLMUsage(
            prompt_tokens=int(
                usage_data.get("prompt_tokens", 0)
            ),
            completion_tokens=int(
                usage_data.get("completion_tokens", 0)
            ),
            total_tokens=int(
                usage_data.get("total_tokens", 0)
            ),
        )

        returned_model = str(
            data.get("model") or self._model
        )

        return LLMResult(
            content=content,
            model=returned_model,
            usage=usage,
            duration_ms=duration_ms,
        )

    def _ensure_configured(self) -> None:
        missing_fields: list[str] = []

        if not self._base_url:
            missing_fields.append("LLM_API_BASE_URL")

        if not self._api_key:
            missing_fields.append("LLM_API_KEY")

        if not self._model:
            missing_fields.append("LLM_MODEL")

        if missing_fields:
            joined_fields = ", ".join(missing_fields)

            raise LLMNotConfiguredError(
                f"missing model configuration: {joined_fields}"
            )

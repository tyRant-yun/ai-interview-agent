import json
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Protocol

import httpx

from app.llm.exceptions import (
    LLMError,
    LLMInvalidResponseError,
    LLMNotConfiguredError,
    LLMTimeoutError,
    LLMUpstreamError,
)
from app.llm.models import (
    LLMMessage,
    LLMResult,
    LLMStreamChunk,
    LLMToolCall,
    LLMToolDecision,
    LLMToolDefinition,
    LLMUsage,
)


class LLMClient(Protocol):
    """Contract required by AI application services."""

    def validate_configuration(self) -> None:
        """Raise when required model configuration is missing."""
        ...

    def generate_json(
        self,
        *,
        messages: list[LLMMessage],
    ) -> LLMResult:
        """Generate one complete JSON response."""
        ...

    def stream_content(
        self,
        *,
        messages: list[LLMMessage],
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream normalized content chunks."""
        ...

    def choose_tools(
        self,
        *,
        messages: list[LLMMessage],
        tools: list[LLMToolDefinition],
    ) -> LLMToolDecision:
        """Allow the model to select zero or more tools."""
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
        stream_include_usage: bool = False,
    ) -> None:
        self._base_url = base_url.rstrip("/") if base_url else None
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._stream_include_usage = stream_include_usage

    def generate_json(
        self,
        *,
        messages: list[LLMMessage],
    ) -> LLMResult:
        self.validate_configuration()

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

    def choose_tools(
        self,
        *,
        messages: list[LLMMessage],
        tools: list[LLMToolDefinition],
    ) -> LLMToolDecision:
        """Ask the model to select a tool without executing it."""

        self.validate_configuration()

        assert self._base_url is not None
        assert self._api_key is not None
        assert self._model is not None

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
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in tools
            ],
            "tool_choice": "auto",
            "temperature": 0.0,
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
                "the tool-selection request timed out"
            ) from error

        except httpx.HTTPStatusError as error:
            body = error.response.text[:500]

            raise LLMUpstreamError(
                "the model service returned "
                f"HTTP {error.response.status_code}: {body}"
            ) from error

        except httpx.HTTPError as error:
            raise LLMUpstreamError(
                "failed to reach the model service: "
                f"{error}"
            ) from error

        duration_ms = int(
            (perf_counter() - started_at) * 1000
        )

        try:
            data = response.json()
            message = data["choices"][0]["message"]

            raw_content = message.get("content")

            if raw_content is not None:
                if not isinstance(raw_content, str):
                    raise TypeError(
                        "assistant content is not a string"
                    )

                content = raw_content.strip() or None
            else:
                content = None

            raw_tool_calls = message.get(
                "tool_calls"
            ) or []

            if not isinstance(raw_tool_calls, list):
                raise TypeError(
                    "tool_calls is not a list"
                )

            tool_calls: list[LLMToolCall] = []

            for raw_call in raw_tool_calls:
                function_data = raw_call["function"]

                call_id = str(raw_call["id"])
                tool_name = str(function_data["name"])
                arguments_json = function_data["arguments"]

                if not isinstance(arguments_json, str):
                    raise TypeError(
                        "tool arguments are not a string"
                    )

                tool_calls.append(
                    LLMToolCall(
                        id=call_id,
                        name=tool_name,
                        arguments_json=arguments_json,
                    )
                )

            if content is None and not tool_calls:
                raise ValueError(
                    "assistant returned neither content "
                    "nor tool calls"
                )

        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
        ) as error:
            raise LLMInvalidResponseError(
                "the model returned an invalid "
                "tool-selection response"
            ) from error

        usage_data = data.get("usage") or {}

        usage = LLMUsage(
            prompt_tokens=int(
                usage_data.get("prompt_tokens", 0)
            ),
            completion_tokens=int(
                usage_data.get(
                    "completion_tokens",
                    0,
                )
            ),
            total_tokens=int(
                usage_data.get("total_tokens", 0)
            ),
        )

        return LLMToolDecision(
            content=content,
            tool_calls=tuple(tool_calls),
            model=str(
                data.get("model") or self._model
            ),
            usage=usage,
            duration_ms=duration_ms,
        )

    async def stream_content(
        self,
        *,
        messages: list[LLMMessage],
    ) -> AsyncIterator[LLMStreamChunk]:
        """Stream content from an OpenAI-compatible endpoint."""

        self.validate_configuration()

        assert self._base_url is not None
        assert self._api_key is not None
        assert self._model is not None

        endpoint = f"{self._base_url}/chat/completions"

        payload: dict[str, object] = {
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
            "stream": True,
        }

        if self._stream_include_usage:
            payload["stream_options"] = {
                "include_usage": True,
            }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
            ) as client:
                async with client.stream(
                    "POST",
                    endpoint,
                    headers=headers,
                    json=payload,
                ) as response:
                    if response.status_code >= 400:
                        response_body = (
                            await response.aread()
                        ).decode(
                            "utf-8",
                            errors="replace",
                        )[:500]

                        raise LLMUpstreamError(
                            "the model service returned "
                            f"HTTP {response.status_code}: "
                            f"{response_body}"
                        )

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        # SSE comments or keep-alive lines.
                        if line.startswith(":"):
                            continue

                        if not line.startswith("data:"):
                            continue

                        raw_data = line.removeprefix(
                            "data:"
                        ).strip()

                        if raw_data == "[DONE]":
                            break

                        try:
                            data = json.loads(raw_data)
                        except json.JSONDecodeError as error:
                            raise LLMInvalidResponseError(
                                "the model stream contained "
                                "invalid JSON"
                            ) from error

                        if data.get("error"):
                            raise LLMUpstreamError(
                                "the model stream returned "
                                f"an error: {data['error']}"
                            )

                        model_value = data.get("model")

                        model = (
                            str(model_value)
                            if model_value is not None
                            else None
                        )

                        usage = None
                        usage_data = data.get("usage")

                        if isinstance(usage_data, dict):
                            usage = LLMUsage(
                                prompt_tokens=int(
                                    usage_data.get(
                                        "prompt_tokens",
                                        0,
                                    )
                                ),
                                completion_tokens=int(
                                    usage_data.get(
                                        "completion_tokens",
                                        0,
                                    )
                                ),
                                total_tokens=int(
                                    usage_data.get(
                                        "total_tokens",
                                        0,
                                    )
                                ),
                            )

                        choices = data.get("choices") or []

                        delta = ""
                        finish_reason = None

                        if choices:
                            choice = choices[0]

                            finish_reason = choice.get(
                                "finish_reason"
                            )

                            delta_data = (
                                choice.get("delta") or {}
                            )

                            content = delta_data.get(
                                "content"
                            )

                            if isinstance(content, str):
                                delta = content

                        yield LLMStreamChunk(
                            delta=delta,
                            model=model,
                            usage=usage,
                            finish_reason=finish_reason,
                        )

        except LLMError:
            raise

        except httpx.TimeoutException as error:
            raise LLMTimeoutError(
                "the streaming model request timed out"
            ) from error

        except httpx.HTTPError as error:
            raise LLMUpstreamError(
                "failed to stream from the model service: "
                f"{error}"
            ) from error

    def validate_configuration(self) -> None:
        """Validate configuration before starting a model request."""

        missing_fields: list[str] = []

        if not self._base_url:
            missing_fields.append("LLM_API_BASE_URL")

        if not self._api_key:
            missing_fields.append("LLM_API_KEY")

        if not self._model:
            missing_fields.append("LLM_MODEL")

        if missing_fields:
            raise LLMNotConfiguredError(
                "missing model configuration: "
                + ", ".join(missing_fields)
            )

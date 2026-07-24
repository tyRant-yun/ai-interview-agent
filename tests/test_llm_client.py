import json

import httpx
import pytest

from app.llm.client import (
    OpenAICompatibleLLMClient,
)
from app.llm.exceptions import (
    LLMToolDecisionProtocolError,
    LLMUpstreamError,
)
from app.llm.models import (
    LLMMessage,
    LLMToolDefinition,
)


def build_client(
    handler,
) -> OpenAICompatibleLLMClient:
    return OpenAICompatibleLLMClient(
        base_url="https://model.example/v1",
        api_key="test-key",
        model="test-model",
        timeout_seconds=5,
        http_transport=httpx.MockTransport(
            handler
        ),
    )


def tool_response(
    *,
    content=None,
    tool_calls=None,
    status_code: int = 200,
) -> httpx.Response:
    return httpx.Response(
        status_code,
        json={
            "model": "provider-model",
            "choices": [
                {
                    "message": {
                        "content": content,
                        "tool_calls": (
                            tool_calls or []
                        ),
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 4,
                "completion_tokens": 2,
                "total_tokens": 6,
            },
        },
    )


def choose(
    client: OpenAICompatibleLLMClient,
    *,
    contract: str = "final_answer_envelope",
):
    return client.choose_tools(
        messages=[
            LLMMessage(
                role="user",
                content="Help me.",
            )
        ],
        tools=[
            LLMToolDefinition(
                name="get_note",
                description="Get one note.",
                parameters={
                    "type": "object",
                    "properties": {},
                },
            )
        ],
        content_contract=contract,
    )


def test_agent_contract_parses_envelope_and_sends_parallel_false():
    requests = []

    def handler(request: httpx.Request):
        requests.append(
            json.loads(request.content)
        )
        return tool_response(
            content=(
                '{"answer":"  Review TCP first.  "}'
            )
        )

    decision = choose(build_client(handler))

    assert decision.content == "Review TCP first."
    assert decision.tool_calls == ()
    assert requests[0][
        "parallel_tool_calls"
    ] is False


@pytest.mark.parametrize(
    "content",
    [
        "plain final answer",
        (
            "<｜｜DSML｜｜tool_calls>"
            '<｜｜DSML｜｜invoke name="get_note">'
        ),
        '{"wrong":"field"}',
        '{"answer":"","extra":true}',
    ],
)
def test_agent_contract_rejects_invalid_content(
    content,
):
    client = build_client(
        lambda request: tool_response(
            content=content
        )
    )

    with pytest.raises(
        LLMToolDecisionProtocolError
    ):
        choose(client)


def test_plain_text_contract_remains_available_for_day8():
    client = build_client(
        lambda request: tool_response(
            content="A plain Day 8 answer."
        )
    )

    decision = choose(
        client,
        contract="plain_text",
    )

    assert decision.content == (
        "A plain Day 8 answer."
    )


def test_native_tool_calls_are_preserved_without_truncation():
    calls = [
        {
            "id": f"call-{index}",
            "type": "function",
            "function": {
                "name": "get_note",
                "arguments": (
                    f'{{"note_id":{index}}}'
                ),
            },
        }
        for index in (1, 2)
    ]

    client = build_client(
        lambda request: tool_response(
            tool_calls=calls
        )
    )

    decision = choose(client)

    assert [
        call.id
        for call in decision.tool_calls
    ] == ["call-1", "call-2"]


@pytest.mark.parametrize(
    "call",
    [
        {
            "id": "call-1",
            "type": "custom",
            "function": {
                "name": "get_note",
                "arguments": "{}",
            },
        },
        {
            "id": 1,
            "type": "function",
            "function": {
                "name": "get_note",
                "arguments": "{}",
            },
        },
        {
            "id": "call-1",
            "type": "function",
            "function": {
                "name": "",
                "arguments": "{}",
            },
        },
    ],
)
def test_native_tool_call_shape_is_strict(
    call,
):
    client = build_client(
        lambda request: tool_response(
            tool_calls=[call]
        )
    )

    with pytest.raises(
        LLMToolDecisionProtocolError
    ):
        choose(client)


def test_tool_call_with_content_is_invalid():
    client = build_client(
        lambda request: tool_response(
            content='{"answer":"not allowed"}',
            tool_calls=[
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {
                        "name": "get_note",
                        "arguments": "{}",
                    },
                }
            ],
        )
    )

    with pytest.raises(
        LLMToolDecisionProtocolError
    ):
        choose(client)


def test_parallel_parameter_unsupported_retries_once():
    payloads = []

    def handler(request: httpx.Request):
        payloads.append(
            json.loads(request.content)
        )

        if len(payloads) == 1:
            return httpx.Response(
                400,
                json={
                    "error": {
                        "message": (
                            "unsupported parameter: "
                            "parallel_tool_calls"
                        )
                    }
                },
            )

        return tool_response(
            content='{"answer":"Done."}'
        )

    decision = choose(build_client(handler))

    assert decision.content == "Done."
    assert len(payloads) == 2
    assert payloads[0][
        "parallel_tool_calls"
    ] is False
    assert "parallel_tool_calls" not in (
        payloads[1]
    )


def test_unrelated_bad_request_does_not_retry():
    request_count = 0

    def handler(request: httpx.Request):
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            400,
            json={
                "error": {
                    "message": "invalid model"
                }
            },
        )

    with pytest.raises(LLMUpstreamError):
        choose(build_client(handler))

    assert request_count == 1

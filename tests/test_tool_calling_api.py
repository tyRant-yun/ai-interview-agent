from app.api.dependencies import (
    NoteManagerDependency,
    get_tool_calling_service,
)
from app.llm.models import (
    LLMToolCall,
    LLMToolDecision,
    LLMUsage,
)
from app.main import app
from app.services.tool_calling import (
    ToolCallingService,
)
from app.tools.note_tools import build_note_tools
from app.tools.registry import ToolRegistry
from tests.fakes import FakeLLMClient


def create_note(
    client,
    *,
    title: str,
    category: str,
    content: str,
    mastery_level: str,
) -> int:
    response = client.post(
        "/notes",
        json={
            "title": title,
            "category": category,
            "content": content,
            "mastery_level": mastery_level,
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def build_tool_decision(
    *,
    content: str | None = None,
    tool_call: LLMToolCall | None = None,
) -> LLMToolDecision:
    tool_calls = (
        ()
        if tool_call is None
        else (tool_call,)
    )

    return LLMToolDecision(
        content=content,
        tool_calls=tool_calls,
        model="fake-model",
        usage=LLMUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
        duration_ms=8,
    )


def install_fake_tool_service(
    decision: LLMToolDecision,
) -> None:
    fake_client = FakeLLMClient(
        "{}",
        tool_decision=decision,
    )

    def override_service(
        manager: NoteManagerDependency,
    ) -> ToolCallingService:
        registry = ToolRegistry(
            build_note_tools(manager)
        )

        return ToolCallingService(
            llm_client=fake_client,
            registry=registry,
        )

    app.dependency_overrides[
        get_tool_calling_service
    ] = override_service

def test_model_selects_search_notes(
    client,
):
    create_note(
        client,
        title="TCP three-way handshake",
        category="computer-network",
        content=(
            "TCP uses SYN, SYN-ACK and ACK."
        ),
        mastery_level="learning",
    )

    create_note(
        client,
        title="MySQL B+ tree",
        category="mysql",
        content="MySQL index structure.",
        mastery_level="mastered",
    )

    decision = build_tool_decision(
        tool_call=LLMToolCall(
            id="call-search-1",
            name="search_notes",
            arguments_json=(
                "{"
                '"query":"TCP",'
                '"category":"computer-network",'
                '"limit":5'
                "}"
            ),
        )
    )

    install_fake_tool_service(decision)

    response = client.post(
        "/tools/execute",
        json={
            "user_request": (
                "查找我的 TCP 学习笔记"
            )
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["assistant_text"] is None

    assert body["tool_call"]["name"] == (
        "search_notes"
    )

    assert body["tool_call"][
        "arguments"
    ]["query"] == "TCP"

    assert body["tool_result"][
        "success"
    ] is True

    assert body["tool_result"][
        "output"
    ]["count"] == 1

    assert body["tool_result"][
        "output"
    ]["notes"][0]["title"] == (
        "TCP three-way handshake"
    )


def test_model_selects_get_weak_topics(
    client,
):
    create_note(
        client,
        title="TCP handshake",
        category="computer-network",
        content="TCP connection setup.",
        mastery_level="learning",
    )

    create_note(
        client,
        title="HTTP status codes",
        category="computer-network",
        content="HTTP response semantics.",
        mastery_level="new",
    )

    create_note(
        client,
        title="DNS resolution",
        category="computer-network",
        content="DNS maps names to addresses.",
        mastery_level="mastered",
    )

    decision = build_tool_decision(
        tool_call=LLMToolCall(
            id="call-weak-1",
            name="get_weak_topics",
            arguments_json=(
                "{"
                '"category":"computer-network",'
                '"limit":5'
                "}"
            ),
        )
    )

    install_fake_tool_service(decision)

    response = client.post(
        "/tools/execute",
        json={
            "user_request": (
                "列出我还没有掌握的网络知识"
            )
        },
    )

    assert response.status_code == 200

    body = response.json()

    result = body["tool_result"]

    assert result["success"] is True
    assert result["output"]["count"] == 2

    returned_titles = [
        note["title"]
        for note in result["output"]["notes"]
    ]

    # NEW topics are ordered before LEARNING topics.
    assert returned_titles == [
        "HTTP status codes",
        "TCP handshake",
    ]


def test_model_can_answer_without_tool(
    client,
):
    decision = build_tool_decision(
        content=(
            "TCP is a transport-layer protocol."
        )
    )

    install_fake_tool_service(decision)

    response = client.post(
        "/tools/execute",
        json={
            "user_request": (
                "简单解释一下 TCP 是什么"
            )
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["assistant_text"] == (
        "TCP is a transport-layer protocol."
    )

    assert body["tool_call"] is None
    assert body["tool_result"] is None


def test_unknown_tool_returns_bad_gateway(
    client,
):
    decision = build_tool_decision(
        tool_call=LLMToolCall(
            id="call-unknown-1",
            name="delete_all_notes",
            arguments_json="{}",
        )
    )

    install_fake_tool_service(decision)

    response = client.post(
        "/tools/execute",
        json={
            "user_request": (
                "删除所有笔记"
            )
        },
    )

    assert response.status_code == 502

    assert response.json()["error"] == (
        "invalid_tool_call"
    )


def test_invalid_tool_arguments_return_bad_gateway(
    client,
):
    decision = build_tool_decision(
        tool_call=LLMToolCall(
            id="call-invalid-1",
            name="search_notes",
            arguments_json=(
                '{"limit":999}'
            ),
        )
    )

    install_fake_tool_service(decision)

    response = client.post(
        "/tools/execute",
        json={
            "user_request": (
                "搜索一些笔记"
            )
        },
    )

    assert response.status_code == 502

    assert response.json()["error"] == (
        "invalid_tool_call"
    )


def test_missing_note_returns_failed_tool_result(
    client,
):
    decision = build_tool_decision(
        tool_call=LLMToolCall(
            id="call-get-999",
            name="get_note",
            arguments_json=(
                '{"note_id":999}'
            ),
        )
    )

    install_fake_tool_service(decision)

    response = client.post(
        "/tools/execute",
        json={
            "user_request": (
                "查看编号 999 的笔记"
            )
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["tool_call"]["name"] == (
        "get_note"
    )

    assert body["tool_result"][
        "success"
    ] is False

    assert body["tool_result"][
        "output"
    ] is None

    assert "not found" in body[
        "tool_result"
    ]["error"]

from app.api.dependencies import (
    NoteManagerDependency,
    get_agent_runner,
)
from app.llm.models import (
    LLMToolCall,
    LLMToolDecision,
    LLMUsage,
)
from app.main import app
from app.services.agent_runner import AgentRunner
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
    """Create one note through the real HTTP API."""

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
    call_id: str,
    tool_name: str,
    arguments_json: str,
) -> LLMToolDecision:
    """Create one fake model decision that calls a tool."""

    return LLMToolDecision(
        content=None,
        tool_calls=(
            LLMToolCall(
                id=call_id,
                name=tool_name,
                arguments_json=arguments_json,
            ),
        ),
        model="fake-model",
        usage=LLMUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
        duration_ms=5,
    )


def build_final_decision(
    answer: str,
) -> LLMToolDecision:
    """Create one fake model decision with a final answer."""

    return LLMToolDecision(
        content=answer,
        tool_calls=(),
        model="fake-model",
        usage=LLMUsage(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
        ),
        duration_ms=5,
    )


def install_fake_agent(
    fake_client: FakeLLMClient,
) -> None:
    """Replace only the model while keeping the real DB tools."""

    def override_runner(
        manager: NoteManagerDependency,
    ) -> AgentRunner:
        registry = ToolRegistry(
            build_note_tools(manager)
        )

        return AgentRunner(
            llm_client=fake_client,
            registry=registry,
        )

    app.dependency_overrides[
        get_agent_runner
    ] = override_runner


def test_agent_uses_weak_topics_then_answers(
    client,
):
    """
    The Agent should:

    1. call get_weak_topics;
    2. execute it against the test database;
    3. receive the tool result;
    4. produce a final answer.
    """

    create_note(
        client,
        title="TCP three-way handshake",
        category="computer-network",
        content=(
            "TCP uses SYN, SYN-ACK and ACK "
            "to establish a connection."
        ),
        mastery_level="learning",
    )

    create_note(
        client,
        title="HTTP status codes",
        category="computer-network",
        content=(
            "HTTP status codes describe "
            "the result of a request."
        ),
        mastery_level="new",
    )

    create_note(
        client,
        title="DNS resolution",
        category="computer-network",
        content=(
            "DNS maps domain names "
            "to IP addresses."
        ),
        mastery_level="mastered",
    )

    fake_client = FakeLLMClient(
        "{}",
        tool_decisions=[
            build_tool_decision(
                call_id="call-weak-1",
                tool_name="get_weak_topics",
                arguments_json=(
                    "{"
                    '"category":"computer-network",'
                    '"limit":5'
                    "}"
                ),
            ),
            build_final_decision(
                "You should review HTTP status "
                "codes first, followed by the "
                "TCP three-way handshake."
            ),
        ],
    )

    install_fake_agent(fake_client)

    response = client.post(
        "/agent/run",
        json={
            "user_request": (
                "根据我的薄弱网络知识安排复习顺序"
            ),
            "max_steps": 2,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["step_count"] == 2

    first_step = body["steps"][0]
    second_step = body["steps"][1]

    assert first_step["step_number"] == 1

    assert first_step["tool_call"][
        "name"
    ] == "get_weak_topics"

    assert first_step["tool_call"][
        "arguments"
    ] == {
        "category": "computer-network",
        "limit": 5,
    }

    assert first_step["tool_result"][
        "success"
    ] is True

    assert first_step["tool_result"][
        "output"
    ]["count"] == 2

    returned_titles = [
        note["title"]
        for note in first_step[
            "tool_result"
        ]["output"]["notes"]
    ]

    # NEW should be returned before LEARNING.
    assert returned_titles == [
        "HTTP status codes",
        "TCP three-way handshake",
    ]

    assert second_step["step_number"] == 2
    assert second_step["tool_call"] is None
    assert second_step["tool_result"] is None

    assert body["final_answer"] == (
        "You should review HTTP status "
        "codes first, followed by the "
        "TCP three-way handshake."
    )

    # Two model calls, 15 tokens each.
    assert body["usage"][
        "total_tokens"
    ] == 30


def test_agent_can_answer_without_tool(
    client,
):
    """
    The model may produce a final answer immediately
    when stored-note data is not required.
    """

    fake_client = FakeLLMClient(
        "{}",
        tool_decisions=[
            build_final_decision(
                "TCP is a reliable, "
                "connection-oriented "
                "transport protocol."
            )
        ],
    )

    install_fake_agent(fake_client)

    response = client.post(
        "/agent/run",
        json={
            "user_request": (
                "用一句话解释 TCP 是什么"
            ),
            "max_steps": 4,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["step_count"] == 1

    assert body["final_answer"] == (
        "TCP is a reliable, "
        "connection-oriented "
        "transport protocol."
    )

    assert body["steps"][0][
        "tool_call"
    ] is None

    assert body["steps"][0][
        "tool_result"
    ] is None

    assert body["usage"][
        "total_tokens"
    ] == 15


def test_agent_single_step_returns_final_answer(
    client,
):
    fake_client = FakeLLMClient(
        "{}",
        tool_decisions=[
            build_final_decision(
                "Review TCP before HTTP."
            )
        ],
    )

    install_fake_agent(fake_client)

    response = client.post(
        "/agent/run",
        json={
            "user_request": (
                "分析我的薄弱网络知识"
            ),
            "max_steps": 1,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["final_answer"] == (
        "Review TCP before HTTP."
    )
    assert body["step_count"] == 1
    assert fake_client.tool_choices == ["none"]


def test_agent_final_turn_tool_call_returns_502(
    client,
):
    fake_client = FakeLLMClient(
        "{}",
        tool_decisions=[
            build_tool_decision(
                call_id="call-weak-1",
                tool_name="get_weak_topics",
                arguments_json=(
                    "{"
                    '"category":"computer-network",'
                    '"limit":5'
                    "}"
                ),
            )
        ],
    )

    install_fake_agent(fake_client)

    response = client.post(
        "/agent/run",
        json={
            "user_request": (
                "分析我的薄弱网络知识"
            ),
            "max_steps": 1,
        },
    )

    assert response.status_code == 502

    body = response.json()

    assert body["error"] == (
        "llm_invalid_response"
    )
    assert "final-answer-only" in body["detail"]

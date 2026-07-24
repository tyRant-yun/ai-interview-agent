import json

from app.api.dependencies import (
    ConversationManagerDependency,
    LLMClientDependency,
    get_conversation_memory_service,
    get_llm_client,
)
from app.llm.models import (
    LLMToolCall,
    LLMToolDecision,
    LLMUsage,
)
from app.llm.exceptions import (
    LLMToolDecisionProtocolError,
)
from app.db.models import (
    ConversationMessageRecord,
)
from app.db.session import SessionLocal
from app.main import app
from app.services.conversation_memory import (
    ConversationMemoryService,
)
from tests.fakes import FakeLLMClient


def build_final_decision(
    answer: str,
) -> LLMToolDecision:
    """Create one deterministic final-answer model turn."""

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


def create_conversation(
    client,
    *,
    title: str | None = None,
) -> int:
    """Create one conversation through the real API."""

    response = client.post(
        "/conversations",
        json={
            "title": title,
        },
    )

    assert response.status_code == 201

    return response.json()["id"]


def install_fake_llm(
    fake_client: FakeLLMClient,
) -> None:
    """
    Replace the real provider while preserving:

    - FastAPI routes;
    - AgentRunner;
    - ConversationManager;
    - SQLAlchemy repositories;
    - test SQLite database.
    """

    app.dependency_overrides[
        get_llm_client
    ] = lambda: fake_client


def install_small_memory_window() -> None:
    """
    Use a small threshold so tests can trigger summary
    compaction after only two conversation turns.
    """

    def override_memory(
        manager: ConversationManagerDependency,
        llm_client: LLMClientDependency,
    ) -> ConversationMemoryService:
        return ConversationMemoryService(
            manager=manager,
            llm_client=llm_client,
            recent_message_limit=2,
            summary_trigger_messages=3,
            context_char_budget=10_000,
        )

    app.dependency_overrides[
        get_conversation_memory_service
    ] = override_memory


def run_conversation_agent(
    client,
    *,
    conversation_id: int,
    user_request: str,
    max_steps: int = 2,
):
    """Run the persistent Agent endpoint."""

    return client.post(
        (
            f"/conversations/"
            f"{conversation_id}/agent"
        ),
        json={
            "user_request": user_request,
            "max_steps": max_steps,
        },
    )


def test_create_and_read_conversation(
    client,
):
    conversation_id = create_conversation(
        client,
        title="Computer network review",
    )

    response = client.get(
        f"/conversations/{conversation_id}"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["id"] == conversation_id

    assert body["title"] == (
        "Computer network review"
    )

    assert body["summary"] is None

    assert body[
        "summarized_through_message_id"
    ] is None

    assert body["messages"] == []


def test_second_turn_receives_first_public_turn(
    client,
):
    """
    After the first turn is saved, the second Agent call
    should receive the first public user/assistant pair.
    """

    fake_client = FakeLLMClient(
        "{}",
        tool_decisions=[
            build_final_decision(
                "First assistant answer."
            ),
            build_final_decision(
                "Second assistant answer."
            ),
        ],
    )

    install_fake_llm(fake_client)

    conversation_id = create_conversation(
        client,
        title="TCP review",
    )

    first_response = run_conversation_agent(
        client,
        conversation_id=conversation_id,
        user_request=(
            "What should I review first?"
        ),
    )

    assert first_response.status_code == 200

    second_response = run_conversation_agent(
        client,
        conversation_id=conversation_id,
        user_request=(
            "Why should I review that first?"
        ),
    )

    assert second_response.status_code == 200

    # First Agent request and second Agent request.
    assert len(
        fake_client.tool_requests
    ) == 2

    second_request_messages = (
        fake_client.tool_requests[1][0]
    )

    public_messages = [
        (
            message.role,
            message.content,
        )
        for message in second_request_messages
        if message.role in {
            "user",
            "assistant",
        }
    ]

    assert public_messages == [
        (
            "user",
            "What should I review first?",
        ),
        (
            "assistant",
            "First assistant answer.",
        ),
        (
            "user",
            "Why should I review that first?",
        ),
    ]

    # Long-term conversation history must not contain
    # tool protocol messages.
    assert all(
        message.role != "tool"
        for message
        in second_request_messages
    )


def test_summary_is_created_after_threshold(
    client,
):
    """
    Two turns produce four public messages.

    With:
        recent_message_limit = 2
        summary_trigger_messages = 3

    The first two messages should be summarized.
    """

    fake_client = FakeLLMClient(
        json.dumps(
            {
                "summary": (
                    "The user is reviewing TCP "
                    "and wants a study order."
                )
            }
        ),
        tool_decisions=[
            build_final_decision(
                "First answer."
            ),
            build_final_decision(
                "Second answer."
            ),
        ],
    )

    install_fake_llm(fake_client)
    install_small_memory_window()

    conversation_id = create_conversation(
        client,
        title="TCP review",
    )

    first_response = run_conversation_agent(
        client,
        conversation_id=conversation_id,
        user_request="First question.",
    )

    assert first_response.status_code == 200

    assert first_response.json()[
        "memory"
    ]["compaction"]["status"] == (
        "not_needed"
    )

    second_response = run_conversation_agent(
        client,
        conversation_id=conversation_id,
        user_request="Second question.",
    )

    assert second_response.status_code == 200

    memory = second_response.json()[
        "memory"
    ]

    assert memory[
        "compaction"
    ]["status"] == "updated"

    assert memory[
        "compaction"
    ]["messages_summarized"] == 2

    conversation_response = client.get(
        f"/conversations/{conversation_id}"
    )

    assert conversation_response.status_code == 200

    conversation = (
        conversation_response.json()
    )

    assert conversation["summary"] == (
        "The user is reviewing TCP "
        "and wants a study order."
    )

    assert conversation[
        "summarized_through_message_id"
    ] is not None

    # Messages remain persisted for audit/history;
    # the summary pointer determines which are compressed
    # when constructing future model context.
    assert len(
        conversation["messages"]
    ) == 4


def test_next_turn_uses_summary_and_recent_messages(
    client,
):
    """
    After compaction:

    - the summary should become a system reference;
    - summarized messages should not be repeated;
    - the latest unsummarized turn should remain verbatim.
    """

    summary_text = (
        "The user is reviewing TCP "
        "and wants a study order."
    )

    fake_client = FakeLLMClient(
        json.dumps(
            {
                "summary": summary_text,
            }
        ),
        tool_decisions=[
            build_final_decision(
                "First answer."
            ),
            build_final_decision(
                "Second answer."
            ),
            build_final_decision(
                "Third answer."
            ),
        ],
    )

    install_fake_llm(fake_client)
    install_small_memory_window()

    conversation_id = create_conversation(
        client,
        title="TCP review",
    )

    run_conversation_agent(
        client,
        conversation_id=conversation_id,
        user_request="First question.",
    )

    second_response = run_conversation_agent(
        client,
        conversation_id=conversation_id,
        user_request="Second question.",
    )

    assert second_response.status_code == 200

    assert second_response.json()[
        "memory"
    ]["compaction"]["status"] == (
        "updated"
    )

    third_response = run_conversation_agent(
        client,
        conversation_id=conversation_id,
        user_request="Third question.",
    )

    assert third_response.status_code == 200

    # Third Agent model request.
    third_request_messages = (
        fake_client.tool_requests[2][0]
    )

    system_contents = [
        message.content
        for message in third_request_messages
        if message.role == "system"
    ]

    assert any(
        summary_text in (
            content or ""
        )
        for content in system_contents
    )

    public_messages = [
        (
            message.role,
            message.content,
        )
        for message in third_request_messages
        if message.role in {
            "user",
            "assistant",
        }
    ]

    # First turn was compressed into summary.
    assert (
        "user",
        "First question.",
    ) not in public_messages

    assert (
        "assistant",
        "First answer.",
    ) not in public_messages

    # Second turn remains in the recent raw window.
    assert (
        "user",
        "Second question.",
    ) in public_messages

    assert (
        "assistant",
        "Second answer.",
    ) in public_messages

    # The current request is always appended last.
    assert public_messages[-1] == (
        "user",
        "Third question.",
    )

    memory = third_response.json()[
        "memory"
    ]

    assert memory["summary_used"] is True

    assert memory[
        "history_messages_used"
    ] == 2


def test_missing_conversation_returns_404(
    client,
):
    response = client.get(
        "/conversations/999"
    )

    assert response.status_code == 404

    assert response.json()["error"] == (
        "conversation_not_found"
    )


def test_missing_conversation_agent_returns_404(
    client,
):
    fake_client = FakeLLMClient(
        "{}",
        tool_decisions=[
            build_final_decision(
                "This should never be used."
            )
        ],
    )

    install_fake_llm(fake_client)

    response = run_conversation_agent(
        client,
        conversation_id=999,
        user_request="Hello.",
    )

    assert response.status_code == 404

    assert response.json()["error"] == (
        "conversation_not_found"
    )

    # The conversation lookup fails before any model call.
    assert fake_client.tool_requests == []


def test_summary_failure_does_not_lose_turn(
    client,
):
    """
    Summary generation is best-effort.

    Invalid summary JSON should report failed compaction,
    while the completed user/assistant turn remains stored.
    """

    fake_client = FakeLLMClient(
        '{"unexpected":"value"}',
        tool_decisions=[
            build_final_decision(
                "First answer."
            ),
            build_final_decision(
                "Second answer."
            ),
        ],
    )

    install_fake_llm(fake_client)
    install_small_memory_window()

    conversation_id = create_conversation(
        client,
        title="Summary failure test",
    )

    first_response = run_conversation_agent(
        client,
        conversation_id=conversation_id,
        user_request="First question.",
    )

    assert first_response.status_code == 200

    second_response = run_conversation_agent(
        client,
        conversation_id=conversation_id,
        user_request="Second question.",
    )

    assert second_response.status_code == 200

    compaction = second_response.json()[
        "memory"
    ]["compaction"]

    assert compaction["status"] == "failed"

    assert compaction[
        "messages_summarized"
    ] == 0

    conversation_response = client.get(
        f"/conversations/{conversation_id}"
    )

    assert conversation_response.status_code == 200

    conversation = (
        conversation_response.json()
    )

    assert conversation["summary"] is None

    # Both completed turns are still stored.
    assert [
        (
            message["role"],
            message["content"],
        )
        for message
        in conversation["messages"]
    ] == [
        (
            "user",
            "First question.",
        ),
        (
            "assistant",
            "First answer.",
        ),
        (
            "user",
            "Second question.",
        ),
        (
            "assistant",
            "Second answer.",
        ),
    ]


def test_invalid_protocol_leaves_message_count_unchanged(
    client,
):
    fake_client = FakeLLMClient(
        "{}",
        tool_decisions=[
            LLMToolDecisionProtocolError(
                "invalid envelope"
            ),
            LLMToolDecisionProtocolError(
                "invalid envelope again"
            ),
        ],
    )
    install_fake_llm(fake_client)

    conversation_id = create_conversation(
        client,
        title="Invalid protocol",
    )

    before = client.get(
        f"/conversations/{conversation_id}"
    ).json()

    response = run_conversation_agent(
        client,
        conversation_id=conversation_id,
        user_request="This must not be saved.",
    )

    assert response.status_code == 502
    assert response.json()["error"] == (
        "llm_invalid_response"
    )

    after = client.get(
        f"/conversations/{conversation_id}"
    ).json()

    assert after["messages"] == before["messages"]
    assert after["summary"] == before["summary"]


def test_multiple_tools_leave_message_count_unchanged(
    client,
):
    multiple = LLMToolDecision(
        content=None,
        tool_calls=(
            LLMToolCall(
                id="call-1",
                name="get_note",
                arguments_json='{"note_id":1}',
            ),
            LLMToolCall(
                id="call-2",
                name="get_note",
                arguments_json='{"note_id":2}',
            ),
        ),
        model="fake-model",
        usage=LLMUsage(),
        duration_ms=1,
    )
    fake_client = FakeLLMClient(
        "{}",
        tool_decisions=[
            multiple,
            multiple,
        ],
    )
    install_fake_llm(fake_client)

    conversation_id = create_conversation(
        client,
        title="Multiple tools",
    )

    response = run_conversation_agent(
        client,
        conversation_id=conversation_id,
        user_request="Do not save this turn.",
    )

    assert response.status_code == 502
    assert response.json()["error"] == (
        "invalid_tool_call"
    )

    conversation = client.get(
        f"/conversations/{conversation_id}"
    ).json()
    assert conversation["messages"] == []


def test_enveloped_dsml_answer_is_not_persisted(
    client,
):
    dsml = (
        "<｜｜DSML｜｜tool_calls>"
        '<｜｜DSML｜｜invoke name="get_note">'
    )
    fake_client = FakeLLMClient(
        "{}",
        tool_decisions=[
            build_final_decision(dsml),
            build_final_decision(dsml),
        ],
    )
    install_fake_llm(fake_client)

    conversation_id = create_conversation(
        client,
        title="DSML envelope",
    )

    response = run_conversation_agent(
        client,
        conversation_id=conversation_id,
        user_request="Do not persist controls.",
    )

    assert response.status_code == 502
    assert response.json()["error"] == (
        "llm_invalid_response"
    )

    conversation = client.get(
        f"/conversations/{conversation_id}"
    ).json()
    assert conversation["messages"] == []


def test_legacy_dsml_turn_is_quarantined_not_deleted(
    client,
):
    fake_client = FakeLLMClient(
        "{}",
        tool_decisions=[
            build_final_decision(
                "A clean current answer."
            )
        ],
    )
    install_fake_llm(fake_client)

    conversation_id = create_conversation(
        client,
        title="Legacy DSML",
    )
    legacy_dsml = (
        "<｜｜DSML｜｜tool_calls>"
        '<｜｜DSML｜｜invoke name="get_all_categories">'
    )

    with SessionLocal() as session:
        session.add_all(
            [
                ConversationMessageRecord(
                    conversation_id=conversation_id,
                    role="user",
                    content="Legacy user request.",
                ),
                ConversationMessageRecord(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=legacy_dsml,
                ),
            ]
        )
        session.commit()

    response = run_conversation_agent(
        client,
        conversation_id=conversation_id,
        user_request="Current request.",
    )

    assert response.status_code == 200

    model_messages = (
        fake_client.tool_requests[0][0]
    )
    assert all(
        message.content
        not in {
            "Legacy user request.",
            legacy_dsml,
        }
        for message in model_messages
    )

    conversation = client.get(
        f"/conversations/{conversation_id}"
    ).json()
    persisted_contents = [
        message["content"]
        for message in conversation["messages"]
    ]

    assert persisted_contents == [
        "Legacy user request.",
        legacy_dsml,
        "Current request.",
        "A clean current answer.",
    ]

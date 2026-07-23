import json

from app.api.dependencies import (
    NoteManagerDependency,
    get_question_generation_service,
)
from app.llm.exceptions import (
    LLMNotConfiguredError,
    LLMTimeoutError,
    LLMUpstreamError,
)
from app.main import app
from app.services.question_generation import (
    QuestionGenerationService,
)
from tests.fakes import FakeLLMClient


def create_note(client) -> int:
    response = client.post(
        "/notes",
        json={
            "title": "TCP three-way handshake",
            "category": "computer-network",
            "content": "TCP uses SYN, SYN-ACK and ACK.",
            "mastery_level": "learning",
        },
    )

    assert response.status_code == 201
    return response.json()["id"]


def install_fake_service(
    fake_client: FakeLLMClient,
) -> None:
    def override_service(
        manager: NoteManagerDependency,
    ) -> QuestionGenerationService:
        return QuestionGenerationService(
            note_manager=manager,
            llm_client=fake_client,
        )

    app.dependency_overrides[
        get_question_generation_service
    ] = override_service


def test_generate_structured_questions(client):
    note_id = create_note(client)

    fake_content = json.dumps(
        {
            "questions": [
                {
                    "question": (
                        "Why does TCP need a "
                        "three-way handshake?"
                    ),
                    "focus": (
                        "bidirectional communication"
                    ),
                    "difficulty": "basic",
                }
            ]
        }
    )

    install_fake_service(
        FakeLLMClient(fake_content)
    )

    response = client.post(
        "/interview/questions",
        json={
            "note_id": note_id,
            "difficulty": "basic",
            "question_count": 1,
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["note_id"] == note_id
    assert body["model"] == "fake-model"
    assert len(body["questions"]) == 1
    assert body["usage"]["total_tokens"] == 30


def test_invalid_model_output_returns_bad_gateway(
    client,
):
    note_id = create_note(client)

    install_fake_service(
        FakeLLMClient(
            '{"unexpected": "response"}'
        )
    )

    response = client.post(
        "/interview/questions",
        json={
            "note_id": note_id,
            "difficulty": "basic",
            "question_count": 1,
        },
    )

    assert response.status_code == 502
    assert response.json()["error"] == (
        "llm_invalid_response"
    )


def test_stream_questions_returns_sse(client):
    note_id = create_note(client)

    fake_content = json.dumps(
        {
            "questions": [
                {
                    "question": (
                        "Why does TCP need a "
                        "three-way handshake?"
                    ),
                    "focus": (
                        "bidirectional communication"
                    ),
                    "difficulty": "basic",
                }
            ]
        }
    )

    install_fake_service(
        FakeLLMClient(fake_content)
    )

    with client.stream(
        "POST",
        "/interview/questions/stream",
        json={
            "note_id": note_id,
            "difficulty": "basic",
            "question_count": 1,
        },
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200

    assert "text/event-stream" in (
        response.headers["content-type"]
    )

    assert "event: started" in body
    assert "event: delta" in body
    assert "event: completed" in body
    assert '"first_token_ms":' in body


def test_invalid_stream_result_emits_error_event(
    client,
):
    note_id = create_note(client)

    install_fake_service(
        FakeLLMClient(
            '{"unexpected":"value"}'
        )
    )

    with client.stream(
        "POST",
        "/interview/questions/stream",
        json={
            "note_id": note_id,
            "difficulty": "basic",
            "question_count": 1,
        },
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert "event: error" in body
    assert "llm_invalid_response" in body


def test_stream_missing_note_returns_404(client):
    response = client.post(
        "/interview/questions/stream",
        json={
            "note_id": 999,
            "difficulty": "basic",
            "question_count": 1,
        },
    )

    assert response.status_code == 404


def test_generate_timeout_returns_gateway_timeout(
    client,
):
    note_id = create_note(client)

    install_fake_service(
        FakeLLMClient(
            "{}",
            generate_error=LLMTimeoutError(
                "the model request timed out"
            ),
        )
    )

    response = client.post(
        "/interview/questions",
        json={
            "note_id": note_id,
            "difficulty": "basic",
            "question_count": 1,
        },
    )

    assert response.status_code == 504
    assert response.json()["error"] == "llm_timeout"


def test_generate_upstream_error_returns_bad_gateway(
    client,
):
    note_id = create_note(client)

    install_fake_service(
        FakeLLMClient(
            "{}",
            generate_error=LLMUpstreamError(
                "upstream service unavailable"
            ),
        )
    )

    response = client.post(
        "/interview/questions",
        json={
            "note_id": note_id,
            "difficulty": "basic",
            "question_count": 1,
        },
    )

    assert response.status_code == 502
    assert response.json()["error"] == (
        "llm_upstream_error"
    )


def test_stream_missing_configuration_returns_503(
    client,
):
    note_id = create_note(client)

    install_fake_service(
        FakeLLMClient(
            "{}",
            config_error=LLMNotConfiguredError(
                "missing model configuration"
            ),
        )
    )

    response = client.post(
        "/interview/questions/stream",
        json={
            "note_id": note_id,
            "difficulty": "basic",
            "question_count": 1,
        },
    )

    assert response.status_code == 503
    assert "application/json" in (
        response.headers["content-type"]
    )
    assert response.json()["error"] == (
        "llm_not_configured"
    )


def test_stream_timeout_emits_error_event(client):
    note_id = create_note(client)

    valid_content = json.dumps(
        {
            "questions": [
                {
                    "question": (
                        "Why does TCP need a "
                        "three-way handshake?"
                    ),
                    "focus": (
                        "bidirectional communication"
                    ),
                    "difficulty": "basic",
                }
            ]
        }
    )

    install_fake_service(
        FakeLLMClient(
            valid_content,
            stream_error=LLMTimeoutError(
                "the streaming request timed out"
            ),
        )
    )

    with client.stream(
        "POST",
        "/interview/questions/stream",
        json={
            "note_id": note_id,
            "difficulty": "basic",
            "question_count": 1,
        },
    ) as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert "event: started" in body
    assert "event: delta" in body
    assert "event: error" in body
    assert "llm_timeout" in body
    assert "event: completed" not in body

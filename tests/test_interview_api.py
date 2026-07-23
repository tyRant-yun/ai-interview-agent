import json

from app.api.dependencies import (
    NoteManagerDependency,
    get_question_generation_service,
)
from app.llm.models import (
    LLMResult,
    LLMUsage,
)
from app.services.question_generation import (
    QuestionGenerationService,
)
from app.main import app


class FakeLLMClient:
    def __init__(self, content: str) -> None:
        self._content = content

    def generate_json(self, *, messages):
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

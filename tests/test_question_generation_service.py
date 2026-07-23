import asyncio
import json

import pytest

from app.domain.interview import (
    InterviewDifficulty,
    QuestionStreamCompleted,
    QuestionStreamDelta,
    QuestionStreamStarted,
)
from app.domain.models import (
    MasteryLevel,
    Note,
)
from app.llm.exceptions import (
    LLMInvalidResponseError,
)
from app.services.question_generation import (
    QuestionGenerationService,
)
from tests.fakes import FakeLLMClient


class StubNoteManager:
    """Minimal note lookup dependency for service tests."""

    def __init__(self) -> None:
        self.note = Note(
            id=1,
            title="TCP three-way handshake",
            category="computer-network",
            content="TCP uses SYN, SYN-ACK and ACK.",
            mastery_level=MasteryLevel.LEARNING,
        )

    def get_note(self, note_id: int) -> Note:
        assert note_id == self.note.id
        return self.note


def build_service(
    content: str,
) -> QuestionGenerationService:
    return QuestionGenerationService(
        note_manager=StubNoteManager(),
        llm_client=FakeLLMClient(content),
    )


def build_question_content(
    *,
    difficulty: str = "basic",
    count: int = 1,
) -> str:
    return json.dumps(
        {
            "questions": [
                {
                    "question": f"Question {index + 1}",
                    "focus": "TCP connection setup",
                    "difficulty": difficulty,
                }
                for index in range(count)
            ]
        }
    )


def test_service_generates_domain_result():
    service = build_service(
        build_question_content()
    )

    result = service.generate_questions(
        note_id=1,
        difficulty=InterviewDifficulty.BASIC,
        question_count=1,
    )

    assert result.note_id == 1
    assert result.topic == (
        "TCP three-way handshake"
    )
    assert len(result.questions) == 1
    assert result.model == "fake-model"
    assert result.usage.total_tokens == 30


def test_service_rejects_wrong_question_count():
    service = build_service(
        build_question_content(count=2)
    )

    with pytest.raises(LLMInvalidResponseError):
        service.generate_questions(
            note_id=1,
            difficulty=InterviewDifficulty.BASIC,
            question_count=1,
        )


def test_service_rejects_wrong_difficulty():
    service = build_service(
        build_question_content(
            difficulty="advanced"
        )
    )

    with pytest.raises(LLMInvalidResponseError):
        service.generate_questions(
            note_id=1,
            difficulty=InterviewDifficulty.BASIC,
            question_count=1,
        )


def test_service_stream_event_order():
    service = build_service(
        build_question_content()
    )

    prepared = service.prepare_questions(
        note_id=1,
        difficulty=InterviewDifficulty.BASIC,
        question_count=1,
    )

    async def collect_updates():
        return [
            update
            async for update in service.stream_questions(
                prepared=prepared
            )
        ]

    updates = asyncio.run(collect_updates())

    assert isinstance(
        updates[0],
        QuestionStreamStarted,
    )

    assert any(
        isinstance(update, QuestionStreamDelta)
        for update in updates
    )

    assert isinstance(
        updates[-1],
        QuestionStreamCompleted,
    )

    completed = updates[-1]

    assert completed.model == "fake-model"
    assert completed.usage is not None
    assert completed.usage.total_tokens == 30
    assert completed.first_token_ms is not None

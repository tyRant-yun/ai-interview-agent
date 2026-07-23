from collections.abc import AsyncIterator
from dataclasses import dataclass
from time import perf_counter

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
)

from app.domain.interview import (
    GeneratedQuestion,
    InterviewDifficulty,
    QuestionGenerationResult,
    QuestionStreamCompleted,
    QuestionStreamDelta,
    QuestionStreamStarted,
    QuestionStreamUpdate,
)
from app.domain.note_manager import NoteManager
from app.llm.client import LLMClient
from app.llm.exceptions import LLMInvalidResponseError
from app.llm.models import LLMMessage
from app.prompts.interview_questions import (
    build_interview_question_messages,
)


@dataclass(frozen=True, slots=True)
class PreparedQuestionGeneration:
    """Validated information required to start generation."""

    note_id: int
    topic: str
    difficulty: InterviewDifficulty
    question_count: int
    messages: tuple[LLMMessage, ...]


class _GeneratedQuestionPayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    question: str = Field(
        min_length=1,
        max_length=1000,
    )

    focus: str = Field(
        min_length=1,
        max_length=500,
    )

    difficulty: InterviewDifficulty


class _QuestionSetPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[_GeneratedQuestionPayload] = Field(
        min_length=1,
        max_length=5,
    )


def _parse_questions(
    *,
    content: str,
    expected_count: int,
    expected_difficulty: InterviewDifficulty,
) -> tuple[GeneratedQuestion, ...]:
    """Validate untrusted model output."""

    try:
        parsed = _QuestionSetPayload.model_validate_json(
            content
        )

    except ValidationError as error:
        raise LLMInvalidResponseError(
            "the model returned JSON that did not "
            "match the question schema"
        ) from error

    if len(parsed.questions) != expected_count:
        raise LLMInvalidResponseError(
            "the model returned an unexpected "
            "number of questions"
        )

    if any(
        item.difficulty != expected_difficulty
        for item in parsed.questions
    ):
        raise LLMInvalidResponseError(
            "the model returned a different difficulty "
            "than requested"
        )

    return tuple(
        GeneratedQuestion(
            question=item.question,
            focus=item.focus,
            difficulty=item.difficulty,
        )
        for item in parsed.questions
    )


class QuestionGenerationService:
    """Generate structured interview questions from a note."""

    def __init__(
        self,
        *,
        note_manager: NoteManager,
        llm_client: LLMClient,
    ) -> None:
        self._note_manager = note_manager
        self._llm_client = llm_client

    def prepare_questions(
        self,
        *,
        note_id: int,
        difficulty: InterviewDifficulty,
        question_count: int,
    ) -> PreparedQuestionGeneration:
        """Run checks that must happen before streaming starts."""

        note = self._note_manager.get_note(note_id)

        self._llm_client.validate_configuration()

        messages = build_interview_question_messages(
            note=note,
            difficulty=difficulty,
            question_count=question_count,
        )

        return PreparedQuestionGeneration(
            note_id=note.id,
            topic=note.title,
            difficulty=difficulty,
            question_count=question_count,
            messages=tuple(messages),
        )

    def generate_questions(
        self,
        *,
        note_id: int,
        difficulty: InterviewDifficulty,
        question_count: int,
    ) -> QuestionGenerationResult:
        """Generate one complete non-streaming result."""

        prepared = self.prepare_questions(
            note_id=note_id,
            difficulty=difficulty,
            question_count=question_count,
        )

        llm_result = self._llm_client.generate_json(
            messages=list(prepared.messages)
        )

        questions = _parse_questions(
            content=llm_result.content,
            expected_count=prepared.question_count,
            expected_difficulty=prepared.difficulty,
        )

        return QuestionGenerationResult(
            note_id=prepared.note_id,
            topic=prepared.topic,
            questions=questions,
            model=llm_result.model,
            usage=llm_result.usage,
            duration_ms=llm_result.duration_ms,
        )

    async def stream_questions(
        self,
        *,
        prepared: PreparedQuestionGeneration,
    ) -> AsyncIterator[QuestionStreamUpdate]:
        """Stream partial text and emit one validated final result."""

        started_at = perf_counter()
        first_token_ms: int | None = None

        content_parts: list[str] = []

        returned_model = ""
        usage = None

        yield QuestionStreamStarted(
            note_id=prepared.note_id,
            topic=prepared.topic,
            difficulty=prepared.difficulty,
            question_count=prepared.question_count,
        )

        async for chunk in self._llm_client.stream_content(
            messages=list(prepared.messages)
        ):
            if chunk.model:
                returned_model = chunk.model

            if chunk.usage is not None:
                usage = chunk.usage

            if not chunk.delta:
                continue

            if first_token_ms is None:
                first_token_ms = int(
                    (perf_counter() - started_at) * 1000
                )

            content_parts.append(chunk.delta)

            yield QuestionStreamDelta(
                text=chunk.delta
            )

        full_content = "".join(content_parts)

        questions = _parse_questions(
            content=full_content,
            expected_count=prepared.question_count,
            expected_difficulty=prepared.difficulty,
        )

        duration_ms = int(
            (perf_counter() - started_at) * 1000
        )

        yield QuestionStreamCompleted(
            note_id=prepared.note_id,
            topic=prepared.topic,
            questions=questions,
            model=returned_model or "unknown",
            usage=usage,
            first_token_ms=first_token_ms,
            duration_ms=duration_ms,
        )

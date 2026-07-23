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
)
from app.domain.note_manager import NoteManager
from app.llm.client import LLMClient
from app.llm.exceptions import LLMInvalidResponseError
from app.prompts.interview_questions import (
    build_interview_question_messages,
)


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

    def generate_questions(
        self,
        *,
        note_id: int,
        difficulty: InterviewDifficulty,
        question_count: int,
    ) -> QuestionGenerationResult:
        note = self._note_manager.get_note(note_id)

        messages = build_interview_question_messages(
            note=note,
            difficulty=difficulty,
            question_count=question_count,
        )

        llm_result = self._llm_client.generate_json(
            messages=messages
        )

        try:
            parsed = _QuestionSetPayload.model_validate_json(
                llm_result.content
            )

        except ValidationError as error:
            raise LLMInvalidResponseError(
                "the model returned JSON that did not "
                "match the question schema"
            ) from error

        if len(parsed.questions) != question_count:
            raise LLMInvalidResponseError(
                "the model returned an unexpected "
                "number of questions"
            )

        if any(
            item.difficulty != difficulty
            for item in parsed.questions
        ):
            raise LLMInvalidResponseError(
                "the model returned a different difficulty "
                "than requested"
            )

        questions = tuple(
            GeneratedQuestion(
                question=item.question,
                focus=item.focus,
                difficulty=item.difficulty,
            )
            for item in parsed.questions
        )

        return QuestionGenerationResult(
            note_id=note.id,
            topic=note.title,
            questions=questions,
            model=llm_result.model,
            usage=llm_result.usage,
            duration_ms=llm_result.duration_ms,
        )

from pydantic import BaseModel, ConfigDict, Field

from app.domain.interview import InterviewDifficulty


class GenerateQuestionsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    note_id: int = Field(gt=0)

    difficulty: InterviewDifficulty = (
        InterviewDifficulty.BASIC
    )

    question_count: int = Field(
        default=3,
        ge=1,
        le=5,
    )


class GeneratedQuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question: str
    focus: str
    difficulty: InterviewDifficulty


class LLMUsageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class QuestionGenerationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    note_id: int
    topic: str
    questions: list[GeneratedQuestionResponse]
    model: str
    usage: LLMUsageResponse
    duration_ms: int

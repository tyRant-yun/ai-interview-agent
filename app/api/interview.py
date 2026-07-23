from fastapi import APIRouter

from app.api.dependencies import (
    QuestionGenerationServiceDependency,
)
from app.api.interview_schemas import (
    GenerateQuestionsRequest,
    QuestionGenerationResponse,
)


router = APIRouter(
    prefix="/interview",
    tags=["interview"],
)


@router.post(
    "/questions",
    response_model=QuestionGenerationResponse,
)
def generate_questions(
    payload: GenerateQuestionsRequest,
    service: QuestionGenerationServiceDependency,
) -> QuestionGenerationResponse:
    result = service.generate_questions(
        note_id=payload.note_id,
        difficulty=payload.difficulty,
        question_count=payload.question_count,
    )

    return QuestionGenerationResponse.model_validate(
        result
    )

from dataclasses import dataclass
from enum import Enum

from app.llm.models import LLMUsage


class InterviewDifficulty(str, Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


@dataclass(frozen=True, slots=True)
class GeneratedQuestion:
    question: str
    focus: str
    difficulty: InterviewDifficulty


@dataclass(frozen=True, slots=True)
class QuestionGenerationResult:
    note_id: int
    topic: str
    questions: tuple[GeneratedQuestion, ...]
    model: str
    usage: LLMUsage
    duration_ms: int

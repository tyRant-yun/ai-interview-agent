from dataclasses import dataclass
from enum import Enum


class MasteryLevel(str, Enum):
    """Learning status of a knowledge note."""

    NEW = "new"
    LEARNING = "learning"
    FAMILIAR = "familiar"
    MASTERED = "mastered"


@dataclass(slots=True)
class Note:
    """A single interview-preparation knowledge note."""

    id: int
    title: str
    category: str
    content: str
    mastery_level: MasteryLevel = MasteryLevel.NEW

    def __post_init__(self) -> None:
        self.title = self.title.strip()
        self.category = self.category.strip()
        self.content = self.content.strip()

        if not self.title:
            raise ValueError("title cannot be empty")

        if not self.category:
            raise ValueError("category cannot be empty")

        if not self.content:
            raise ValueError("content cannot be empty")

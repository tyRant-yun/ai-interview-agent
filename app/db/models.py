from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NoteRecord(Base):
    """Database representation of a knowledge note."""

    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    title: Mapped[str] = mapped_column(
        String(200),
        unique=True,
        index=True,
        nullable=False,
    )

    category: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    mastery_level: Mapped[str] = mapped_column(
        String(20),
        index=True,
        nullable=False,
    )

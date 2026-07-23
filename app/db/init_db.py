from app.db.base import Base
from app.db.models import NoteRecord
from app.db.session import engine


def create_db_and_tables() -> None:
    """Create database tables that do not already exist."""

    _ = NoteRecord
    Base.metadata.create_all(bind=engine)

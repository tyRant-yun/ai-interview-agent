import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./app.db",
)

connect_args: dict[str, object] = {}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False


engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def get_session() -> Generator[Session, None, None]:
    """Provide one database session for one request."""

    with SessionLocal() as session:
        yield session

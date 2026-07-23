import os
import tempfile
from pathlib import Path

import pytest


TEST_DIRECTORY = Path(tempfile.mkdtemp())
TEST_DATABASE = TEST_DIRECTORY / "test.db"

os.environ["DATABASE_URL"] = (
    f"sqlite:///{TEST_DATABASE.as_posix()}"
)


from starlette.testclient import TestClient

from app.db.base import Base
from app.db.session import engine
from app.main import app


@pytest.fixture(autouse=True)
def reset_database():
    app.dependency_overrides.clear()

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

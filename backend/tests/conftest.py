"""Shared test fixtures.

Point the app at a throwaway SQLite file before anything imports `app.core.config`, so the
lifespan's `create_all` never touches the real dev database. This module is imported by
pytest before test modules, so setting the env var here is early enough.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_cinerex.db"

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture()
def client():
    # The context manager runs startup/shutdown (lifespan → init_db).
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True, scope="session")
def _cleanup_test_db():
    yield
    # Dispose the engine first: on Windows an open SQLite handle blocks file removal.
    from app.db.session import engine

    engine.dispose()
    try:
        os.remove("./test_cinerex.db")
    except (FileNotFoundError, PermissionError):
        pass

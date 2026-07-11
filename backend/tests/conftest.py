"""Shared test fixtures.

Point the app at a throwaway SQLite file before anything imports `app.core.config`, so the
lifespan's `create_all` never touches the real dev database. This module is imported by
pytest before test modules, so setting the env var here is early enough.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_cinerex.db"
# Hermetic tests: blank TMDB keys (present env vars override the repo .env) so no test ever
# reaches the live API. Tests that need matches inject a FakeTMDB explicitly.
os.environ["TMDB_API_KEY"] = ""
os.environ["TMDB_BEARER_TOKEN"] = ""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture()
def client():
    # The context manager runs startup/shutdown (lifespan → init_db).
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _fresh_tables():
    """Recreate all tables around each test so rows never leak between tests."""
    from app.db.session import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True, scope="session")
def _cleanup_test_db():
    yield
    from app.db.session import engine

    engine.dispose()  # release the SQLite handle so Windows lets us delete the file
    try:
        os.remove("./test_cinerex.db")
    except (FileNotFoundError, PermissionError):
        pass

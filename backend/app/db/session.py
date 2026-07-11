"""SQLAlchemy engine + session, driven entirely by `DATABASE_URL`.

Database-agnostic by design (PLAN.md constraint 6): no SQLite-specific SQL, no raw PRAGMA.
A local `sqlite:///` file and a production `sqlite+libsql://` Turso URL are one connection
string apart. The only scheme-specific handling here is a connect arg SQLite needs to be
used across FastAPI's threadpool and the background job worker.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings


def _make_engine(url: str):
    connect_args: dict = {}
    is_libsql = "+libsql" in url  # Turso: sqlite+libsql://<db>.turso.io/?authToken=...&secure=true
    if url.startswith("sqlite") and not is_libsql:
        # Local SQLite file is touched from multiple threads (request threadpool + ingest worker),
        # so disable pysqlite's single-thread guard. The libSQL client manages its own threading
        # and the auth token rides in the URL, so no connect_args are needed there.
        connect_args["check_same_thread"] = False
    return create_engine(url, future=True, connect_args=connect_args)


engine = _make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

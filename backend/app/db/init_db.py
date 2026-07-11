"""Create all tables on startup.

v1 has no migrations (PLAN.md): tables self-create from the SQLAlchemy metadata, and a
database reset is just deleting the local SQLite file. Importing `app.models` ensures every
model is registered on `Base.metadata` before `create_all` runs. In Phase 0 there are no
models yet, so this is a no-op that becomes load-bearing in Phase 1.
"""

from app.db.session import Base, engine
from app import models  # noqa: F401  — registers models on Base.metadata


def init_db() -> None:
    Base.metadata.create_all(bind=engine)

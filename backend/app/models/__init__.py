"""SQLAlchemy models package.

Importing `entities` registers every model on `Base.metadata` so `init_db.create_all`
creates their tables on startup.
"""

from app.models.entities import (  # noqa: F401
    Film,
    IngestJob,
    LetterboxdTmdbCache,
    Profile,
    TasteProfile,
    WatchHistory,
)

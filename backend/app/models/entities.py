"""v1 data model.

Thin and un-authenticated by design (PLAN.md §1a): a Profile is a `handle`, not a login.
Accounts arrive in v1.1 as a separate table, not a rewrite of this one. There are no
migrations in v1 — tables self-create from this metadata; a reset is deleting the DB file.
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    # Naive UTC, stored consistently so downstream date math never mixes tz-aware/naive.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Profile(Base):
    """Anonymous, public, un-owned identity. `handle` is a label, not a credential."""

    __tablename__ = "profiles"

    handle: Mapped[str] = mapped_column(String, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    last_ingest_at: Mapped[datetime | None] = mapped_column(DateTime)


class Film(Base):
    """A TMDB-enriched film. Shared across profiles; enrichment amortizes via the cache."""

    __tablename__ = "films"
    __table_args__ = (UniqueConstraint("tmdb_id", "media_type"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(String, nullable=False, default="film")
    imdb_id: Mapped[str | None] = mapped_column(String)
    title: Mapped[str] = mapped_column(String, nullable=False)
    original_title: Mapped[str | None] = mapped_column(String)
    release_year: Mapped[int | None] = mapped_column(Integer)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer)
    overview: Mapped[str | None] = mapped_column(Text)
    original_language: Mapped[str | None] = mapped_column(String)
    genres: Mapped[list | None] = mapped_column(JSON)
    keywords: Mapped[list | None] = mapped_column(JSON)                 # for Phase 3 embeddings
    crew: Mapped[dict | None] = mapped_column(JSON)                     # {director, cinematographer, composer}
    tmdb_rating: Mapped[float | None] = mapped_column(Float)            # vote_average → contrarianism
    tmdb_vote_count: Mapped[int | None] = mapped_column(Integer)        # → obscurity preference
    poster_path: Mapped[str | None] = mapped_column(String)
    backdrop_path: Mapped[str | None] = mapped_column(String)
    # 384-dim MiniLM vector of overview+genres+keywords, cached (it never changes). Added in Phase 3;
    # v1 has no migrations, so a DB reset (delete the SQLite file) picks up the new column.
    embedding: Mapped[list | None] = mapped_column(JSON)


class WatchHistory(Base):
    """One row per (profile, film). Re-ingest updates in place — never duplicates."""

    __tablename__ = "watch_history"
    __table_args__ = (UniqueConstraint("profile_handle", "film_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    profile_handle: Mapped[str] = mapped_column(
        ForeignKey("profiles.handle", ondelete="CASCADE"), nullable=False
    )
    film_id: Mapped[str] = mapped_column(ForeignKey("films.id"), nullable=False)
    user_rating: Mapped[float | None] = mapped_column(Float)            # 0.5–5.0, or None (logged unrated)
    watched_at: Mapped[date | None] = mapped_column(Date)
    is_rewatch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    review_text: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String, default="upload", nullable=False)  # upload | sync


class TasteProfile(Base):
    """The computed portrait. `evidence_json` (Phase 2) + `summary` prose (Phase 4)."""

    __tablename__ = "taste_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    profile_handle: Mapped[str] = mapped_column(
        ForeignKey("profiles.handle", ondelete="CASCADE"), nullable=False, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)
    evidence_json: Mapped[dict | None] = mapped_column(JSON)
    summary: Mapped[str | None] = mapped_column(Text)


class IngestJob(Base):
    """Async job tracking upload/sync → enrich → (analyze) → complete, with progress."""

    __tablename__ = "ingest_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    profile_handle: Mapped[str] = mapped_column(
        ForeignKey("profiles.handle", ondelete="CASCADE"), nullable=False
    )
    source: Mapped[str] = mapped_column(String, nullable=False)          # upload | sync
    # queued | parsing | enriching | analyzing | complete | failed
    status: Mapped[str] = mapped_column(String, default="queued", nullable=False)
    step: Mapped[str | None] = mapped_column(String)
    films_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    films_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    films_matched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    films_unmatched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class LetterboxdTmdbCache(Base):
    """Slug → TMDB match cache. Amortizes the expensive title-matching across all users."""

    __tablename__ = "letterboxd_tmdb_cache"
    __table_args__ = (UniqueConstraint("lookup_key"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    # Stable per-film key: the Letterboxd slug when we have one, else "title::year".
    lookup_key: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String)
    release_year: Mapped[int | None] = mapped_column(Integer)
    tmdb_id: Mapped[int | None] = mapped_column(Integer)
    matched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

import uuid
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    email: Mapped[str | None] = mapped_column(String, unique=True)
    display_name: Mapped[str | None] = mapped_column(String)
    country_code: Mapped[str] = mapped_column(String, default="US", nullable=False)
    preferred_format: Mapped[str] = mapped_column(String, default="both", nullable=False)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    sync_status: Mapped[str] = mapped_column(String, default="pending", nullable=False)
    sync_error: Mapped[str | None] = mapped_column(Text)


class LetterboxdProfile(Base):
    __tablename__ = "letterboxd_profiles"
    __table_args__ = (UniqueConstraint("user_id", "username"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False)
    profile_url: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String)
    avatar_url: Mapped[str | None] = mapped_column(String)
    bio: Mapped[str | None] = mapped_column(Text)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime)
    total_films: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class SerializdProfile(Base):
    __tablename__ = "serializd_profiles"
    __table_args__ = (UniqueConstraint("user_id", "username"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    username: Mapped[str] = mapped_column(String, nullable=False)
    profile_url: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime)
    total_shows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_private: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class Film(Base):
    __tablename__ = "films"
    __table_args__ = (UniqueConstraint("tmdb_id", "media_type"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(String, nullable=False)
    imdb_id: Mapped[str | None] = mapped_column(String)
    title: Mapped[str] = mapped_column(String, nullable=False)
    original_title: Mapped[str | None] = mapped_column(String)
    release_year: Mapped[int | None] = mapped_column(Integer)
    runtime_minutes: Mapped[int | None] = mapped_column(Integer)
    overview: Mapped[str | None] = mapped_column(Text)
    original_language: Mapped[str | None] = mapped_column(String)
    genres: Mapped[list | None] = mapped_column(JSON)
    tmdb_rating: Mapped[float | None] = mapped_column(Float)
    tmdb_vote_count: Mapped[int | None] = mapped_column(Integer)
    poster_path: Mapped[str | None] = mapped_column(String)
    backdrop_path: Mapped[str | None] = mapped_column(String)


class WatchHistory(Base):
    __tablename__ = "watch_history"
    __table_args__ = (UniqueConstraint("user_id", "film_id", "source"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    film_id: Mapped[str] = mapped_column(ForeignKey("films.id"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    user_rating: Mapped[float | None] = mapped_column(Float)
    watched_at: Mapped[date | None] = mapped_column(Date)
    is_rewatch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    watch_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    review_text: Mapped[str | None] = mapped_column(Text)
    review_liked: Mapped[bool | None] = mapped_column(Boolean)
    letterboxd_id: Mapped[str | None] = mapped_column(String)


class Watchlist(Base):
    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("user_id", "film_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    film_id: Mapped[str] = mapped_column(ForeignKey("films.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    source: Mapped[str] = mapped_column(String, default="letterboxd", nullable=False)
    rank: Mapped[int | None] = mapped_column(Integer)
    rank_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)


class StreamingService(Base):
    __tablename__ = "streaming_services"
    __table_args__ = (UniqueConstraint("user_id", "provider_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    provider_id: Mapped[int] = mapped_column(Integer, nullable=False)
    provider_name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class TasteProfile(Base):
    __tablename__ = "taste_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    taste_summary: Mapped[str] = mapped_column(Text, nullable=False)


class LetterboxdTmdbCache(Base):
    __tablename__ = "letterboxd_tmdb_cache"
    __table_args__ = (UniqueConstraint("letterboxd_slug"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    letterboxd_slug: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str | None] = mapped_column(String)
    release_year: Mapped[int | None] = mapped_column(Integer)
    tmdb_id: Mapped[int | None] = mapped_column(Integer)
    matched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, default="started", nullable=False)
    step: Mapped[str | None] = mapped_column(String)
    films_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    films_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

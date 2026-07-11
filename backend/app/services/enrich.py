"""TMDB enrichment + the async ingest job.

Resolves each parsed film to TMDB (cache-first, so matching amortizes across users), upserts the
shared `Film` row with one details+credits+keywords call, and writes per-profile `WatchHistory`.
The job reports progress (enriching → complete) and counts matched vs unmatched — unmatched films
are recorded in the cache and counted, never silently dropped.

Adapted from the archive's sync.py `_get_or_create_film`; the network/DB shape is the same, the
identity (profile handle) and the crew/keyword capture are new.
"""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.entities import (
    Film,
    IngestJob,
    LetterboxdTmdbCache,
    Profile,
    WatchHistory,
    utcnow,
)
from app.services.ingest import ParsedFilm
from app.services.tmdb import TMDBService

_PROGRESS_FLUSH_EVERY = 10


class EnrichmentService:
    def __init__(self, tmdb: TMDBService | None = None) -> None:
        self.tmdb = tmdb or TMDBService()

    def resolve_film(self, db: Session, parsed: ParsedFilm) -> Film | None:
        """Return the enriched Film for a parsed entry, or None if TMDB can't match it."""
        cache = db.query(LetterboxdTmdbCache).filter_by(lookup_key=parsed.lookup_key).first()

        if cache and cache.matched:
            tmdb_id = cache.tmdb_id
        elif cache and not cache.matched:
            return None  # previously determined unmatchable — don't hit the API again
        else:
            try:
                result = self.tmdb.search_movie_match(parsed.title, parsed.year)
            except Exception:  # noqa: BLE001 — network/HTTP errors → treat as no match
                result = None
            if not result:
                db.add(
                    LetterboxdTmdbCache(
                        lookup_key=parsed.lookup_key,
                        title=parsed.title,
                        release_year=parsed.year,
                        matched=False,
                    )
                )
                db.commit()
                return None
            tmdb_id = result["id"]
            db.add(
                LetterboxdTmdbCache(
                    lookup_key=parsed.lookup_key,
                    title=parsed.title,
                    release_year=parsed.year,
                    tmdb_id=tmdb_id,
                    matched=True,
                )
            )
            db.commit()

        film = db.query(Film).filter_by(tmdb_id=tmdb_id, media_type="film").first()
        if film:
            return film

        try:
            details = self.tmdb.movie_details(tmdb_id, append="credits,keywords")
        except Exception:  # noqa: BLE001
            details = {}

        return self._insert_film(db, tmdb_id, self._film_from_details(tmdb_id, details, parsed))

    def _insert_film(self, db: Session, tmdb_id: int, film: Film) -> Film | None:
        """Insert a Film, tolerating a concurrent request that inserted the same one first."""
        try:
            db.add(film)
            db.commit()
            db.refresh(film)
            return film
        except IntegrityError:
            db.rollback()
            return db.query(Film).filter_by(tmdb_id=tmdb_id, media_type="film").first()

    def get_or_create_by_tmdb_id(self, db: Session, tmdb_id: int) -> Film | None:
        """Fetch/create a Film from a known TMDB id (no title search). Used for ranker candidates."""
        film = db.query(Film).filter_by(tmdb_id=tmdb_id, media_type="film").first()
        if film:
            return film
        try:
            details = self.tmdb.movie_details(tmdb_id, append="credits,keywords")
        except Exception:  # noqa: BLE001
            return None
        if not details or not details.get("id"):
            return None
        parsed = ParsedFilm(title=details.get("title") or "", year=None, slug=None)
        return self._insert_film(db, tmdb_id, self._film_from_details(tmdb_id, details, parsed))

    def _film_from_details(self, tmdb_id: int, details: dict, parsed: ParsedFilm) -> Film:
        release = details.get("release_date") or ""
        release_year = int(release[:4]) if release[:4].isdigit() else parsed.year
        return Film(
            tmdb_id=tmdb_id,
            media_type="film",
            imdb_id=details.get("imdb_id"),
            title=details.get("title") or parsed.title,
            original_title=details.get("original_title"),
            release_year=release_year,
            runtime_minutes=details.get("runtime"),
            overview=details.get("overview"),
            original_language=details.get("original_language"),
            genres=[g.get("name") for g in details.get("genres", []) if g.get("name")],
            keywords=self._extract_keywords(details),
            crew=self._extract_crew(details.get("credits") or {}),
            tmdb_rating=details.get("vote_average"),
            tmdb_vote_count=details.get("vote_count"),
            poster_path=details.get("poster_path"),
            backdrop_path=details.get("backdrop_path"),
        )

    @staticmethod
    def _extract_keywords(details: dict) -> list[str]:
        kw = (details.get("keywords") or {}).get("keywords", []) or []
        return [k.get("name") for k in kw if k.get("name")]

    @staticmethod
    def _extract_crew(credits: dict) -> dict:
        crew = credits.get("crew", []) or []

        def names(jobs: set[str]) -> list[str]:
            seen: list[str] = []
            for member in crew:
                if member.get("job") in jobs and member.get("name") and member["name"] not in seen:
                    seen.append(member["name"])
            return seen

        return {
            "director": names({"Director"}),
            "cinematographer": names({"Director of Photography", "Cinematography"}),
            "composer": names({"Original Music Composer", "Music"}),
        }

    def upsert_watch(
        self, db: Session, profile_handle: str, film: Film, parsed: ParsedFilm, source: str
    ) -> None:
        existing = (
            db.query(WatchHistory)
            .filter_by(profile_handle=profile_handle, film_id=film.id)
            .first()
        )
        if existing:
            if parsed.rating is not None:
                existing.user_rating = parsed.rating
            if parsed.watched_at:
                existing.watched_at = parsed.watched_at
            existing.is_rewatch = existing.is_rewatch or parsed.is_rewatch
            if parsed.review_text:
                existing.review_text = parsed.review_text
        else:
            db.add(
                WatchHistory(
                    profile_handle=profile_handle,
                    film_id=film.id,
                    user_rating=parsed.rating,
                    watched_at=parsed.watched_at,
                    is_rewatch=parsed.is_rewatch,
                    review_text=parsed.review_text,
                    source=source,
                )
            )


def enrich_into(
    db: Session,
    job: IngestJob,
    profile_handle: str,
    parsed_films: list[ParsedFilm],
    source: str,
    svc: EnrichmentService,
) -> tuple[int, int]:
    """Enrich films into the DB, updating job progress. Returns (matched, unmatched). Does not set
    the job's terminal status — the caller decides what happens after enrichment (analyze, complete)."""
    job.status = "enriching"
    job.step = "Matching films on TMDB"
    job.films_total = len(parsed_films)
    db.commit()

    matched = 0
    unmatched = 0
    for idx, parsed in enumerate(parsed_films, start=1):
        try:
            film = svc.resolve_film(db, parsed)
        except Exception:  # noqa: BLE001 — a single bad film never fails the whole job
            db.rollback()
            film = None
        if film is not None:
            svc.upsert_watch(db, profile_handle, film, parsed, source)
            matched += 1
        else:
            unmatched += 1

        job.films_processed = idx
        job.films_matched = matched
        job.films_unmatched = unmatched
        if idx % _PROGRESS_FLUSH_EVERY == 0 or idx == len(parsed_films):
            db.commit()

    profile = db.get(Profile, profile_handle)
    if profile:
        profile.last_ingest_at = utcnow()
    db.commit()
    return matched, unmatched


def run_ingest_job(
    job_id: str,
    profile_handle: str,
    parsed_films: list[ParsedFilm],
    source: str = "upload",
    tmdb: TMDBService | None = None,
    session_factory=SessionLocal,
) -> None:
    """Enrich-only job (no analyze step). Retained for unit tests and the sync path; the full
    upload pipeline uses pipeline.run_full_ingest, which adds evidence + summary."""
    svc = EnrichmentService(tmdb=tmdb)
    db = session_factory()
    try:
        job = db.get(IngestJob, job_id)
        if job is None:
            return
        enrich_into(db, job, profile_handle, parsed_films, source, svc)
        job.status = "complete"
        job.step = "Done"
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        job = db.get(IngestJob, job_id)
        if job:
            job.status = "failed"
            job.error_code = "INGEST_FAILED"
            job.error_message = str(exc)
            db.commit()
    finally:
        db.close()

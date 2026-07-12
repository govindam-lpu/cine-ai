"""TMDB enrichment + the async ingest job.

Resolves each parsed film to TMDB (cache-first, so matching amortizes across users), upserts the
shared `Film` row with one details+credits+keywords call, and writes per-profile `WatchHistory`.
The job reports progress (enriching → complete) and counts matched vs unmatched — unmatched films
are recorded in the cache and counted, never silently dropped.

Adapted from the archive's sync.py `_get_or_create_film`; the network/DB shape is the same, the
identity (profile handle) and the crew/keyword capture are new.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
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

_PROGRESS_FLUSH_EVERY = 100
_BLANK = ParsedFilm(title="", year=None, slug=None)


def _chunks(seq: list, size: int):
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


class EnrichmentService:
    def __init__(self, tmdb: TMDBService | None = None) -> None:
        self.tmdb = tmdb or TMDBService()

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
    the job's terminal status — the caller decides what happens after enrichment (analyze, complete).

    The TMDB calls are the slow part (network-bound, ~1.7s/film serially), so they run concurrently
    while every DB read and write stays on this thread — SQLite has a single writer, and a Session is
    not thread-safe, so the workers only touch the network. Cache-first semantics are preserved: a
    known film is never searched again, and an already-stored Film is never re-fetched.
    """
    job.status = "enriching"
    job.step = "Matching films on TMDB"
    job.films_total = len(parsed_films)
    job.films_processed = 0
    job.films_matched = 0
    job.films_unmatched = 0
    db.commit()

    workers = max(1, settings.tmdb_concurrency)

    # --- Phase 1: plan from the shared cache (one bulk read, no network) ---
    keys = list({p.lookup_key for p in parsed_films})
    cache_by_key: dict[str, LetterboxdTmdbCache] = {}
    for chunk in _chunks(keys, 400):
        for row in db.query(LetterboxdTmdbCache).filter(LetterboxdTmdbCache.lookup_key.in_(chunk)):
            cache_by_key[row.lookup_key] = row

    tmdb_id_by_key: dict[str, int] = {}
    rep_parsed_by_id: dict[int, ParsedFilm] = {}   # a representative parsed film per tmdb_id
    to_search: dict[str, ParsedFilm] = {}
    unmatched = 0
    for parsed in parsed_films:
        cached = cache_by_key.get(parsed.lookup_key)
        if cached is None:
            to_search.setdefault(parsed.lookup_key, parsed)
        elif cached.matched:
            tmdb_id_by_key[parsed.lookup_key] = cached.tmdb_id
            rep_parsed_by_id.setdefault(cached.tmdb_id, parsed)
        else:
            unmatched += 1

    processed = len(parsed_films) - len(to_search)
    job.films_processed = processed
    job.films_unmatched = unmatched
    db.commit()

    # --- Phase 2: concurrent TMDB search for the unknowns (network only) ---
    if to_search:
        new_cache: list[LetterboxdTmdbCache] = []
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as pool:
            fut_key = {
                pool.submit(svc.tmdb.search_movie_match, parsed.title, parsed.year): key
                for key, parsed in to_search.items()
            }
            for fut in as_completed(fut_key):
                key = fut_key[fut]
                parsed = to_search[key]
                try:
                    result = fut.result()
                except Exception:  # noqa: BLE001 — one bad lookup never fails the job
                    result = None
                if result and result.get("id"):
                    tid = result["id"]
                    tmdb_id_by_key[key] = tid
                    rep_parsed_by_id.setdefault(tid, parsed)
                    new_cache.append(
                        LetterboxdTmdbCache(
                            lookup_key=key, title=parsed.title, release_year=parsed.year,
                            tmdb_id=tid, matched=True,
                        )
                    )
                else:
                    unmatched += 1
                    new_cache.append(
                        LetterboxdTmdbCache(
                            lookup_key=key, title=parsed.title, release_year=parsed.year, matched=False,
                        )
                    )
                done += 1
                processed += 1
                if done % _PROGRESS_FLUSH_EVERY == 0:
                    job.films_processed = processed
                    job.films_unmatched = unmatched
                    db.commit()
        db.add_all(new_cache)
        job.films_processed = processed
        job.films_unmatched = unmatched
        db.commit()

    # --- Phase 3: fetch details concurrently for films not yet stored, then insert on this thread ---
    job.step = "Fetching film details"
    db.commit()
    wanted_ids = sorted(set(tmdb_id_by_key.values()))
    films_by_id: dict[int, Film] = {}
    for chunk in _chunks(wanted_ids, 400):
        for film in db.query(Film).filter(Film.tmdb_id.in_(chunk), Film.media_type == "film"):
            films_by_id[film.tmdb_id] = film
    to_fetch = [tid for tid in wanted_ids if tid not in films_by_id]

    if to_fetch:
        details_by_id: dict[int, dict] = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            fut_id = {
                pool.submit(svc.tmdb.movie_details, tid, "credits,keywords"): tid for tid in to_fetch
            }
            for fut in as_completed(fut_id):
                tid = fut_id[fut]
                try:
                    details_by_id[tid] = fut.result() or {}
                except Exception:  # noqa: BLE001
                    details_by_id[tid] = {}

        new_films = {
            tid: svc._film_from_details(tid, details_by_id.get(tid) or {}, rep_parsed_by_id.get(tid, _BLANK))
            for tid in to_fetch
        }
        db.add_all(new_films.values())
        try:
            db.commit()
            for tid, film in new_films.items():
                db.refresh(film)
                films_by_id[tid] = film
        except IntegrityError:
            # Rare: a concurrent job inserted the same Film. Rebuild and insert one-by-one.
            db.rollback()
            for tid in to_fetch:
                rebuilt = svc._film_from_details(
                    tid, details_by_id.get(tid) or {}, rep_parsed_by_id.get(tid, _BLANK)
                )
                persisted = svc._insert_film(db, tid, rebuilt)
                if persisted is not None:
                    films_by_id[tid] = persisted

    # --- Phase 4: write per-profile watch history (main thread) ---
    job.step = "Saving your history"
    matched = 0
    for idx, parsed in enumerate(parsed_films, start=1):
        tid = tmdb_id_by_key.get(parsed.lookup_key)
        film = films_by_id.get(tid) if tid is not None else None
        if film is not None:
            svc.upsert_watch(db, profile_handle, film, parsed, source)
            matched += 1
        if idx % _PROGRESS_FLUSH_EVERY == 0:
            db.commit()

    unmatched = len(parsed_films) - matched
    job.films_matched = matched
    job.films_unmatched = unmatched
    job.films_processed = len(parsed_films)

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

import threading
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.entities import Film, LetterboxdProfile, LetterboxdTmdbCache, ScrapeJob, User, WatchHistory
from app.scrapers.letterboxd import LetterboxdScraper, ScrapeError
from app.services.tmdb import TMDBService

LETTERBOXD_SYNC_LOCK = threading.Lock()


class SyncService:
    def __init__(self) -> None:
        self.scraper = LetterboxdScraper()
        self.tmdb = TMDBService()

    def run_letterboxd_sync(self, db: Session, job_id: str, user_id: str, username: str, mode: str) -> None:
        acquired = LETTERBOXD_SYNC_LOCK.acquire(blocking=False)
        if not acquired:
            self._set_job_error(db, job_id, "ALREADY_SYNCING", "Another Letterboxd scrape is running")
            return

        try:
            job = db.get(ScrapeJob, job_id)
            job.status = "scraping"
            job.step = "Scraping Letterboxd films"
            db.commit()

            scraped = self.scraper.scrape_films(username=username, mode=mode)
            if not scraped:
                raise ScrapeError("NO_FILMS_FOUND", "No public Letterboxd films were found")
            job.films_total = len(scraped)
            job.status = "enriching"
            job.step = "Enriching TMDB metadata"
            db.commit()

            for idx, film_entry in enumerate(scraped, start=1):
                film_row = self._get_or_create_film(db, film_entry.letterboxd_slug, film_entry.title, film_entry.year, film_entry.tmdb_id)
                if film_row:
                    existing = (
                        db.query(WatchHistory)
                        .filter_by(user_id=user_id, film_id=film_row.id, source="letterboxd")
                        .first()
                    )
                    if not existing:
                        db.add(
                            WatchHistory(
                                user_id=user_id,
                                film_id=film_row.id,
                                source="letterboxd",
                                user_rating=film_entry.user_rating,
                                watched_at=film_entry.watched_at.date() if film_entry.watched_at else None,
                                is_rewatch=film_entry.is_rewatch,
                            )
                        )
                    else:
                        existing.user_rating = film_entry.user_rating if film_entry.user_rating is not None else existing.user_rating
                        existing.watched_at = film_entry.watched_at.date() if film_entry.watched_at else existing.watched_at
                        existing.is_rewatch = existing.is_rewatch or film_entry.is_rewatch
                job.films_processed = idx
                job.updated_at = datetime.utcnow()
                db.commit()

            user = db.get(User, user_id)
            user.sync_status = "complete"
            user.last_synced_at = datetime.utcnow()
            user.sync_error = None
            profile = db.query(LetterboxdProfile).filter_by(user_id=user_id).first()
            if profile:
                profile.total_films = len(scraped)
                profile.last_scraped_at = datetime.utcnow()
                profile.updated_at = datetime.utcnow()

            job.status = "complete"
            job.step = "Done"
            job.updated_at = datetime.utcnow()
            db.commit()

        except ScrapeError as exc:
            self._set_job_error(db, job_id, exc.code, exc.message)
            user = db.get(User, user_id)
            user.sync_status = "error"
            user.sync_error = exc.message
            db.commit()
        except Exception as exc:  # noqa: BLE001
            self._set_job_error(db, job_id, "SCRAPE_FAILED", str(exc))
            user = db.get(User, user_id)
            if user:
                user.sync_status = "error"
                user.sync_error = str(exc)
                db.commit()
        finally:
            LETTERBOXD_SYNC_LOCK.release()

    def _get_or_create_film(self, db: Session, slug: str, title: str, year: int | None, known_tmdb_id: int | None = None) -> Film | None:
        cached = db.query(LetterboxdTmdbCache).filter_by(letterboxd_slug=slug).first()
        tmdb_id = None
        if known_tmdb_id:
            tmdb_id = known_tmdb_id
            if not cached:
                db.add(LetterboxdTmdbCache(letterboxd_slug=slug, title=title, release_year=year, tmdb_id=tmdb_id, matched=True))
                db.commit()
            elif not cached.matched or cached.tmdb_id != tmdb_id:
                cached.tmdb_id = tmdb_id
                cached.matched = True
                db.commit()
        elif cached and cached.matched:
            tmdb_id = cached.tmdb_id
        elif cached and not cached.matched:
            return None
        else:
            try:
                result = self.tmdb.search_movie_match(title=title, year=year)
            except Exception:  # noqa: BLE001
                result = None
            if not result:
                db.add(LetterboxdTmdbCache(letterboxd_slug=slug, title=title, release_year=year, matched=False))
                db.commit()
                return None
            tmdb_id = result["id"]
            db.add(LetterboxdTmdbCache(letterboxd_slug=slug, title=title, release_year=year, tmdb_id=tmdb_id, matched=True))
            db.commit()

        film = db.query(Film).filter_by(tmdb_id=tmdb_id, media_type="film").first()
        if film:
            return film

        try:
            details = self.tmdb.movie_details(tmdb_id)
        except Exception:  # noqa: BLE001
            details = {}
        film = Film(
            tmdb_id=tmdb_id,
            media_type="film",
            imdb_id=details.get("imdb_id"),
            title=details.get("title") or title,
            original_title=details.get("original_title"),
            release_year=int(details.get("release_date", "0000")[:4]) if details.get("release_date") else year,
            runtime_minutes=details.get("runtime"),
            overview=details.get("overview"),
            original_language=details.get("original_language"),
            genres=[g.get("name") for g in details.get("genres", [])],
            tmdb_rating=details.get("vote_average"),
            tmdb_vote_count=details.get("vote_count"),
            poster_path=details.get("poster_path"),
            backdrop_path=details.get("backdrop_path"),
        )
        db.add(film)
        db.commit()
        db.refresh(film)
        return film

    @staticmethod
    def _set_job_error(db: Session, job_id: str, code: str, message: str) -> None:
        job = db.get(ScrapeJob, job_id)
        if not job:
            return
        job.status = "error"
        job.error_code = code
        job.error_message = message
        job.updated_at = datetime.utcnow()
        db.commit()

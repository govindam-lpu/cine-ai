"""Local-dev sync: scraped entries converge on the same enrichment as upload (network-free)."""

from app.db.session import SessionLocal
from app.models.entities import Film, IngestJob, Profile, WatchHistory
from app.scrapers.letterboxd import FilmEntry
from app.services.sync import run_sync_job
from tests.helpers import FakeTMDB
from tests.test_enrich import _details


class _FakeScraper:
    def __init__(self, entries):
        self.entries = entries

    def scrape_films(self, username, mode="full"):
        return self.entries


def _new_sync_job(handle="cinephile") -> str:
    db = SessionLocal()
    try:
        if db.get(Profile, handle) is None:
            db.add(Profile(handle=handle))
        job = IngestJob(profile_handle=handle, source="sync", status="queued")
        db.add(job)
        db.commit()
        db.refresh(job)
        return job.id
    finally:
        db.close()


def test_sync_uses_rss_tmdb_id_and_enriches():
    # Scraped entry carries a TMDB id (RSS fallback) → cache pre-seed → no title search needed.
    entries = [
        FilmEntry(
            title="The Matrix",
            year=1999,
            letterboxd_slug="/film/the-matrix/",
            user_rating=5.0,
            tmdb_id=603,
        )
    ]
    tmdb = FakeTMDB(matches={}, details={603: _details(603, "The Matrix")})
    job_id = _new_sync_job()

    run_sync_job(job_id, "cinephile", tmdb=tmdb, scraper=_FakeScraper(entries))

    db = SessionLocal()
    try:
        assert tmdb.search_calls == 0            # pre-seeded cache short-circuited the search
        film = db.query(Film).filter_by(tmdb_id=603).one()
        watch = db.query(WatchHistory).filter_by(profile_handle="cinephile").one()
        assert watch.film_id == film.id
        assert watch.source == "sync"
        job = db.get(IngestJob, job_id)
        assert job.status == "complete"
        assert job.films_matched == 1
    finally:
        db.close()


def test_sync_scrape_failure_marks_job_failed():
    from app.scrapers.letterboxd import ScrapeError

    class _BlockedScraper:
        def scrape_films(self, username, mode="full"):
            raise ScrapeError("SCRAPE_BLOCKED", "Blocked by Letterboxd/Cloudflare")

    job_id = _new_sync_job()
    run_sync_job(job_id, "cinephile", tmdb=FakeTMDB({}, {}), scraper=_BlockedScraper())

    db = SessionLocal()
    try:
        job = db.get(IngestJob, job_id)
        assert job.status == "failed"
        assert job.error_code == "SCRAPE_BLOCKED"
    finally:
        db.close()

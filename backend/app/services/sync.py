"""Local-dev scrape sync → the same enrichment job as upload.

Only reachable when `allow_scrape_sync` is on (never on the deployed Space — Cloudflare 403s
datacenter IPs). Scrapes a Letterboxd username, converts scraped entries to the same ParsedFilm
shape the CSV path produces, pre-seeds the cache with any TMDB IDs the RSS feed carried, then
hands off to run_ingest_job so both paths converge.
"""

from app.db.session import SessionLocal
from app.models.entities import IngestJob, LetterboxdTmdbCache
from app.scrapers.letterboxd import FilmEntry, LetterboxdScraper, ScrapeError
from app.services.enrich import run_ingest_job
from app.services.ingest import ParsedFilm, slug_from_uri
from app.services.tmdb import TMDBService


def _entry_to_parsed(entry: FilmEntry) -> ParsedFilm:
    return ParsedFilm(
        title=entry.title,
        year=entry.year,
        slug=slug_from_uri(entry.letterboxd_slug),
        rating=entry.user_rating,
        watched_at=entry.watched_at.date() if entry.watched_at else None,
        is_rewatch=entry.is_rewatch,
    )


def run_sync_job(
    job_id: str,
    username: str,
    tmdb: TMDBService | None = None,
    session_factory=SessionLocal,
    scraper: LetterboxdScraper | None = None,
) -> None:
    scraper = scraper or LetterboxdScraper()
    db = session_factory()
    parsed: list[ParsedFilm] = []
    try:
        job = db.get(IngestJob, job_id)
        if job is None:
            return
        job.status = "parsing"
        job.step = "Scraping Letterboxd"
        db.commit()

        try:
            entries = scraper.scrape_films(username, mode="full")
        except ScrapeError as exc:
            job.status = "failed"
            job.error_code = exc.code
            job.error_message = exc.message
            db.commit()
            return

        parsed = [_entry_to_parsed(entry) for entry in entries]
        for entry, film in zip(entries, parsed):
            if entry.tmdb_id:
                existing = (
                    db.query(LetterboxdTmdbCache).filter_by(lookup_key=film.lookup_key).first()
                )
                if existing is None:
                    db.add(
                        LetterboxdTmdbCache(
                            lookup_key=film.lookup_key,
                            title=entry.title,
                            release_year=entry.year,
                            tmdb_id=entry.tmdb_id,
                            matched=True,
                        )
                    )
        db.commit()
    finally:
        db.close()

    # Converge on the shared enrichment loop (opens its own session).
    run_ingest_job(job_id, username, parsed, source="sync", tmdb=tmdb, session_factory=session_factory)

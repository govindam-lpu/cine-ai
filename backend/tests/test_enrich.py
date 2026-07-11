"""Enrichment tests: matched + unmatched paths, cache reuse, crew/keywords, idempotent re-ingest."""

from app.db.session import SessionLocal
from app.models.entities import Film, IngestJob, LetterboxdTmdbCache, Profile, WatchHistory
from app.services.enrich import run_ingest_job
from app.services.ingest import ParsedFilm
from tests.helpers import FakeTMDB


def _details(tmdb_id, title, year="1999"):
    return {
        "id": tmdb_id,
        "title": title,
        "release_date": f"{year}-03-31",
        "runtime": 136,
        "overview": "A hacker learns reality is a simulation.",
        "original_language": "en",
        "genres": [{"name": "Action"}, {"name": "Science Fiction"}],
        "vote_average": 8.2,
        "vote_count": 24000,
        "credits": {
            "crew": [
                {"job": "Director", "name": "Lana Wachowski"},
                {"job": "Director", "name": "Lilly Wachowski"},
                {"job": "Director of Photography", "name": "Bill Pope"},
                {"job": "Original Music Composer", "name": "Don Davis"},
            ]
        },
        "keywords": {"keywords": [{"name": "simulated reality"}, {"name": "artificial intelligence"}]},
    }


def _new_job(handle="tester", source="upload") -> str:
    db = SessionLocal()
    try:
        if db.get(Profile, handle) is None:
            db.add(Profile(handle=handle))
        job = IngestJob(profile_handle=handle, source=source, status="queued")
        db.add(job)
        db.commit()
        db.refresh(job)
        return job.id
    finally:
        db.close()


def test_matched_creates_film_watch_and_completes():
    tmdb = FakeTMDB(matches={"The Matrix": {"id": 603}}, details={603: _details(603, "The Matrix")})
    parsed = [ParsedFilm(title="The Matrix", year=1999, slug="the-matrix", rating=5.0)]
    job_id = _new_job()

    run_ingest_job(job_id, "tester", parsed, "upload", tmdb=tmdb)

    db = SessionLocal()
    try:
        film = db.query(Film).filter_by(tmdb_id=603).one()
        assert film.genres == ["Action", "Science Fiction"]
        assert film.crew["director"] == ["Lana Wachowski", "Lilly Wachowski"]
        assert film.crew["cinematographer"] == ["Bill Pope"]
        assert film.crew["composer"] == ["Don Davis"]
        assert "simulated reality" in film.keywords
        assert film.tmdb_vote_count == 24000

        watch = db.query(WatchHistory).filter_by(profile_handle="tester").one()
        assert watch.user_rating == 5.0
        assert watch.film_id == film.id

        job = db.get(IngestJob, job_id)
        assert job.status == "complete"
        assert job.films_matched == 1
        assert job.films_unmatched == 0
        assert db.get(Profile, "tester").last_ingest_at is not None
    finally:
        db.close()


def test_unmatched_is_recorded_and_counted_not_dropped():
    tmdb = FakeTMDB(matches={}, details={})   # nothing matches
    parsed = [ParsedFilm(title="Some Obscure Film", year=1970, slug="some-obscure-film", rating=3.0)]
    job_id = _new_job()

    run_ingest_job(job_id, "tester", parsed, "upload", tmdb=tmdb)

    db = SessionLocal()
    try:
        assert db.query(Film).count() == 0
        assert db.query(WatchHistory).count() == 0
        cache = db.query(LetterboxdTmdbCache).filter_by(lookup_key="some-obscure-film").one()
        assert cache.matched is False
        job = db.get(IngestJob, job_id)
        assert job.status == "complete"
        assert job.films_matched == 0
        assert job.films_unmatched == 1
    finally:
        db.close()


def test_cache_hit_avoids_second_tmdb_search():
    tmdb = FakeTMDB(matches={"The Matrix": {"id": 603}}, details={603: _details(603, "The Matrix")})
    parsed = [ParsedFilm(title="The Matrix", year=1999, slug="the-matrix", rating=5.0)]

    run_ingest_job(_new_job(), "tester", parsed, "upload", tmdb=tmdb)
    assert tmdb.search_calls == 1
    assert tmdb.details_calls == 1

    # A different profile ingests the same film — the slug cache should short-circuit the search,
    # and the existing Film row should avoid a second details fetch.
    run_ingest_job(_new_job(handle="tester2"), "tester2", parsed, "upload", tmdb=tmdb)
    assert tmdb.search_calls == 1
    assert tmdb.details_calls == 1


def test_reingest_updates_watch_in_place_no_duplicate():
    tmdb = FakeTMDB(matches={"The Matrix": {"id": 603}}, details={603: _details(603, "The Matrix")})
    first = [ParsedFilm(title="The Matrix", year=1999, slug="the-matrix", rating=4.0)]
    second = [ParsedFilm(title="The Matrix", year=1999, slug="the-matrix", rating=5.0, is_rewatch=True)]

    run_ingest_job(_new_job(), "tester", first, "upload", tmdb=tmdb)
    run_ingest_job(_new_job(), "tester", second, "upload", tmdb=tmdb)

    db = SessionLocal()
    try:
        rows = db.query(WatchHistory).filter_by(profile_handle="tester").all()
        assert len(rows) == 1                     # updated, not duplicated
        assert rows[0].user_rating == 5.0
        assert rows[0].is_rewatch is True
    finally:
        db.close()


def test_unconfigured_tmdb_marks_all_unmatched_without_crashing():
    # The real TMDBService with no keys returns {} everywhere → every film unmatched, job completes.
    from app.services.tmdb import TMDBService

    parsed = [ParsedFilm(title="The Matrix", year=1999, slug="the-matrix", rating=5.0)]
    job_id = _new_job()

    run_ingest_job(job_id, "tester", parsed, "upload", tmdb=TMDBService())

    db = SessionLocal()
    try:
        job = db.get(IngestJob, job_id)
        assert job.status == "complete"
        assert job.films_unmatched == 1
    finally:
        db.close()

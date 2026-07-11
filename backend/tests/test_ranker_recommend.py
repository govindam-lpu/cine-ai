"""recommend() supplements from the enriched-film cache when TMDB discovery is empty — and still
never returns a watched film."""

from app.db.session import SessionLocal
from app.models.entities import Film, Profile, WatchHistory
from app.services.ranker import ensure_film_embeddings, recommend
from tests.helpers import FakeTMDB

_EVIDENCE = {
    "baseline_rating": 3.8,
    "seeds": {"genres": ["Drama"], "decades": [], "languages": []},
    "genre_affinity": [],
    "era_affinity": [],
    "crew_affinity": {"director": []},
    "obscurity_preference": {"value": None},
    "patience": {"value": None},
    "contrarianism": {"value": None},
}


def test_recommend_falls_back_to_cached_films_when_discovery_empty():
    db = SessionLocal()
    try:
        db.add(Profile(handle="u"))
        watched = [
            Film(tmdb_id=100 + i, media_type="film", title=f"W{i}",
                 overview=f"a slow drama number {i}", genres=["Drama"])
            for i in range(3)
        ]
        candidates = [
            Film(tmdb_id=200 + i, media_type="film", title=f"C{i}",
                 overview=f"a tense thriller number {i}", genres=["Thriller"])
            for i in range(5)
        ]
        db.add_all(watched + candidates)
        db.commit()
        for f in watched:
            db.refresh(f)
        for rating, f in zip([5.0, 4.5, 2.0], watched):
            db.add(WatchHistory(profile_handle="u", film_id=f.id, user_rating=rating))
        db.commit()
        ensure_film_embeddings(db, watched + candidates)

        # Empty discovery → must fall back to the 5 cached candidates.
        recs = recommend(db, "u", _EVIDENCE, tmdb=FakeTMDB({}, {}, discover=[]), limit=8)

        watched_ids = {100, 101, 102}
        assert 1 <= len(recs) <= 5
        assert all(r.tmdb_id not in watched_ids for r in recs)   # invariant holds under fallback
        assert all(r.tmdb_id >= 200 for r in recs)               # only the unwatched candidates
    finally:
        db.close()

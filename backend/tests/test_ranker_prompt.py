"""Free-text prompt (real fastembed): the user's request steers the ranking in embedding space,
and maps to sensible discovery genres — all without the LLM deciding anything (constraint 2)."""

import numpy as np

from app.services.embeddings import embed_texts
from app.services.ranker import FilmVector, build_taste_vector, genres_for_prompt, rank_candidates
from tests.helpers import ROMCOM_TEXTS, SCIFI_TEXTS


def _embed(text: str) -> np.ndarray:
    return embed_texts([text])[0]


def test_prompt_steers_ranking_toward_the_request():
    # Taste loves sci-fi and romcom equally (zero variance → centroid fallback), so similarity alone
    # barely separates the two candidates. The prompt then decides which comes first.
    rated = [(_embed(t), 5.0) for t in SCIFI_TEXTS[:5]] + [(_embed(t), 5.0) for t in ROMCOM_TEXTS[:5]]
    taste = build_taste_vector(rated, baseline=5.0)
    assert taste is not None

    scifi = FilmVector(tmdb_id=1, title="SciFi", embedding=_embed(SCIFI_TEXTS[6]), genres=["Science Fiction"])
    romcom = FilmVector(tmdb_id=2, title="RomCom", embedding=_embed(ROMCOM_TEXTS[6]), genres=["Romance"])

    recs = rank_candidates(
        taste, [scifi, romcom], watched_ids=set(), evidence={}, limit=2,
        prompt_vec=_embed("a warm, funny romantic comedy about falling in love"),
        prompt_text="something romantic and funny",
    )
    assert recs[0].tmdb_id == 2                                        # the request pulls romcom up
    prompt_signal = next((s for s in recs[0].signals if s["factor"] == "prompt"), None)
    assert prompt_signal is not None                                  # and the card can say why
    assert "romantic and funny" in prompt_signal["detail"]

    # A different request flips the order — proof it's the prompt doing the steering, not a tie-break.
    recs2 = rank_candidates(
        taste, [scifi, romcom], watched_ids=set(), evidence={}, limit=2,
        prompt_vec=_embed("a cerebral science fiction film about space and consciousness"),
    )
    assert recs2[0].tmdb_id == 1


def test_prompt_maps_to_sensible_discovery_genres():
    # A clearly-genred request seeds discovery with the matching TMDB genre (embedding-space, no LLM).
    assert "Horror" in genres_for_prompt(_embed("a terrifying horror movie about a haunted house"))
    assert "Romance" in genres_for_prompt(_embed("a sweet romance about two people falling in love"))


def test_prompt_beats_taste_the_original_bug():
    # The bug the user hit: taste strongly favors sci-fi, but a "romantic comedy" request must return
    # the romcom, not the taste film. In prompt mode the request leads and taste only personalizes.
    rated = [(_embed(t), 5.0) for t in SCIFI_TEXTS[:6]] + [(_embed(t), 1.5) for t in ROMCOM_TEXTS[:6]]
    taste = build_taste_vector(rated, baseline=3.25)  # points hard at sci-fi

    scifi = FilmVector(tmdb_id=1, title="SciFi", embedding=_embed(SCIFI_TEXTS[7]),
                       genres=["Science Fiction"])
    romcom = FilmVector(tmdb_id=2, title="RomCom", embedding=_embed(ROMCOM_TEXTS[7]),
                        genres=["Romance", "Comedy"])

    recs = rank_candidates(
        taste, [scifi, romcom], watched_ids=set(), evidence={}, limit=2,
        prompt_vec=_embed("a romantic comedy"), prompt_text="a romantic comedy",
        prompt_genre_wts={"Romance": 0.20, "Comedy": 0.12},
    )
    assert recs[0].tmdb_id == 2                                          # request wins over taste
    assert recs[0].signals[0]["factor"] in ("prompt", "genre")          # and it says why (not taste)


def test_recommend_with_intent_excludes_standup_and_keeps_comedies():
    """Intent-driven search: exclude_terms drops a standup special even though it's Comedy-tagged and
    high-rated, and the real comedies survive — the 'good movies, not bad ones' guarantee."""
    from app.db.session import SessionLocal
    from app.models.entities import Film, Profile, WatchHistory
    from app.services.ranker import ensure_film_embeddings, recommend
    from tests.helpers import FakeTMDB

    evidence = {
        "baseline_rating": 3.8, "seeds": {"genres": ["Drama"]},
        "genre_affinity": [], "era_affinity": [], "crew_affinity": {"director": []},
        "obscurity_preference": {"value": None}, "patience": {"value": None},
    }

    db = SessionLocal()
    try:
        db.add(Profile(handle="pi"))
        rated = [Film(tmdb_id=300 + i, media_type="film", title=f"R{i}",
                      overview=f"a serious drama number {i}", genres=["Drama"]) for i in range(3)]
        db.add_all(rated)
        db.commit()
        for f in rated:
            db.refresh(f)
        for rating, f in zip([5.0, 4.0, 2.0], rated):
            db.add(WatchHistory(profile_handle="pi", film_id=f.id, user_rating=rating))
        db.commit()
        ensure_film_embeddings(db, rated)

        details = {
            2001: {"id": 2001, "title": "Good Comedy", "genres": [{"name": "Comedy"}],
                   "overview": "a warm feel-good comedy about old friends reuniting",
                   "vote_average": 7.8, "vote_count": 500},
            2002: {"id": 2002, "title": "Sweet Romcom", "genres": [{"name": "Comedy"}, {"name": "Romance"}],
                   "overview": "a charming romantic comedy set in Rome", "vote_average": 7.5, "vote_count": 400},
            2003: {"id": 2003, "title": "Live Special", "genres": [{"name": "Comedy"}],
                   "overview": "the comedian performs a stand-up set recorded live on stage",
                   "vote_average": 8.6, "vote_count": 300},
        }
        tmdb = FakeTMDB(matches={}, details=details, discover=[{"id": 2001}, {"id": 2002}, {"id": 2003}])
        intent = {"genres": ["Comedy"], "exclude_genres": ["Horror"], "keywords": [],
                  "exclude_terms": ["stand-up"], "min_rating": None, "query": "a warm feel-good comedy"}

        recs = recommend(db, "pi", evidence, tmdb=tmdb, prompt="feel good comedy", intent=intent, limit=8)
        titles = {r.title for r in recs}
        assert "Live Special" not in titles          # standup dropped despite an 8.6 rating + Comedy tag
        assert {"Good Comedy", "Sweet Romcom"} <= titles
    finally:
        db.close()

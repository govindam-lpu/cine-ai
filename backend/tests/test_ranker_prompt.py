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

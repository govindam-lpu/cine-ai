"""Taste vector (real fastembed): a viewer who loves one region of taste ranks films in that
region above films outside it. Plus the embedding cache: a film is embedded once, not twice."""

import numpy as np

from app.services.embeddings import embed_texts
from app.services.ranker import FilmVector, build_taste_vector, rank_candidates
from tests.helpers import ROMCOM_TEXTS, SCIFI_TEXTS


def _embed(text: str) -> np.ndarray:
    return embed_texts([text])[0]


def test_loved_region_ranks_above_disliked_region():
    # Loves cerebral sci-fi (5.0), dislikes romcom (1.5) → taste points toward sci-fi.
    rated = [(_embed(t), 5.0) for t in SCIFI_TEXTS[:6]]
    rated += [(_embed(t), 1.5) for t in ROMCOM_TEXTS[:6]]
    taste = build_taste_vector(rated, baseline=3.25)
    assert taste is not None

    scifi_cand = FilmVector(tmdb_id=1, title="New SciFi", embedding=_embed(SCIFI_TEXTS[7]),
                            genres=["Science Fiction"])
    romcom_cand = FilmVector(tmdb_id=2, title="New RomCom", embedding=_embed(ROMCOM_TEXTS[7]),
                             genres=["Romance"])

    recs = rank_candidates(taste, [romcom_cand, scifi_cand], watched_ids=set(), evidence={}, limit=2)
    assert recs[0].tmdb_id == 1                      # sci-fi ranks first
    assert recs[0].similarity > recs[1].similarity   # and by similarity, not tie-break


def test_embeddings_cached_and_not_recomputed(monkeypatch):
    import app.services.ranker as ranker_mod
    from app.db.session import SessionLocal
    from app.models.entities import Film

    calls = {"n": 0}
    real = ranker_mod.embed_texts

    def spy(texts):
        calls["n"] += 1
        return real(texts)

    monkeypatch.setattr(ranker_mod, "embed_texts", spy)

    db = SessionLocal()
    try:
        film = Film(
            tmdb_id=999, media_type="film", title="X",
            overview="A cerebral film about space, memory and consciousness.",
            genres=["Science Fiction"], keywords=["space", "memory"],
        )
        db.add(film)
        db.commit()
        db.refresh(film)

        assert ranker_mod.ensure_film_embeddings(db, [film]) == 1
        assert calls["n"] == 1
        assert film.embedding is not None and len(film.embedding) == 384

        # Second pass: already cached → no re-embed.
        assert ranker_mod.ensure_film_embeddings(db, [film]) == 0
        assert calls["n"] == 1
    finally:
        db.close()

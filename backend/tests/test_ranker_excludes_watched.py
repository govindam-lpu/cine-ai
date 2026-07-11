"""The hard invariant: a watched film never appears in recommendations. Filtered in Python,
both at discovery and at ranking. Property-style over many random watched sets."""

import numpy as np

from app.services.embeddings import EMBED_DIM
from app.services.ranker import FilmVector, discover_candidate_ids, rank_candidates


def _unit(rng) -> np.ndarray:
    v = rng.standard_normal(EMBED_DIM).astype(np.float32)
    return v / np.linalg.norm(v)


def test_watched_never_appears_over_random_sets():
    rng = np.random.default_rng(0)
    for trial in range(20):
        taste = _unit(rng)
        watched = set(int(x) for x in rng.choice(range(1, 60), size=8, replace=False))
        candidates = []
        # candidate pool deliberately includes the watched ids
        for tid in range(1, 60):
            candidates.append(FilmVector(tmdb_id=tid, title=f"F{tid}", embedding=_unit(rng)))
        recs = rank_candidates(taste, candidates, watched, evidence={}, limit=8)
        assert len(recs) == 8
        assert all(r.tmdb_id not in watched for r in recs), f"trial {trial}: leaked a watched film"


def test_ranking_dedupes_by_tmdb_id():
    rng = np.random.default_rng(1)
    taste = _unit(rng)
    v = _unit(rng)
    candidates = [FilmVector(tmdb_id=7, title="dupe", embedding=v) for _ in range(5)]
    recs = rank_candidates(taste, candidates, watched_ids=set(), evidence={}, limit=8)
    assert len(recs) == 1


def test_discovery_filters_watched_ids():
    class _FakeTMDB:
        def discover_movies(self, params):
            if params.get("page", 1) > 1:
                return {"results": []}
            return {"results": [{"id": i} for i in range(1, 21)]}

    evidence = {"seeds": {"genres": ["Drama"], "languages": ["en"], "decades": ["1970s"]}}
    watched = {1, 2, 3, 4, 5}
    ids = discover_candidate_ids(_FakeTMDB(), evidence, watched, target=60)
    assert all(i not in watched for i in ids)
    assert set(ids) == set(range(6, 21))

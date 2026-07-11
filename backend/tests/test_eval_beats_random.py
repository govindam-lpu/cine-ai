"""The held-out evaluation IS the product quality. Hold out a fraction of the viewer's rated films,
build the taste vector from the rest, and check higher-rated held-out films score above lower-rated
ones (pairwise AUC). It must clear random (0.5) by a clear margin."""

import numpy as np

from app.services.embeddings import embed_texts
from app.services.ranker import evaluate_ranking
from tests.helpers import ROMCOM_TEXTS, SCIFI_TEXTS


def _embed_all(texts):
    return embed_texts(list(texts))


def test_holdout_auc_beats_random_by_clear_margin():
    scifi = list(zip(_embed_all(SCIFI_TEXTS), [5.0] * len(SCIFI_TEXTS)))
    romcom = list(zip(_embed_all(ROMCOM_TEXTS), [1.5] * len(ROMCOM_TEXTS)))
    rated = scifi + romcom

    # Average across seeds so the assertion doesn't hinge on one lucky holdout split.
    aucs = []
    for seed in range(5):
        result = evaluate_ranking(rated, holdout_frac=0.3, seed=seed)
        if result["auc"] is not None:
            aucs.append(result["auc"])

    assert aucs, "eval produced no AUC"
    mean_auc = float(np.mean(aucs))
    assert mean_auc >= 0.75, f"AUC {mean_auc:.3f} did not beat random by a clear margin"


def test_eval_reports_insufficient_for_tiny_profiles():
    rated = list(zip(embed_texts(SCIFI_TEXTS[:3]), [5.0, 4.0, 3.0]))
    result = evaluate_ranking(rated)
    assert result["auc"] is None
    assert "too few" in result["reason"]

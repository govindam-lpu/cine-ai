"""Evidence tests: signals point the right way on hand-built viewers; degenerate input is safe."""

from datetime import date

from app.services.evidence import (
    MIN_FILMS,
    WatchDatum,
    build_evidence,
    check_gate,
)

NOW = date(2026, 7, 11)


def w(rating, **kw) -> WatchDatum:
    return WatchDatum(rating=rating, **kw)


# --- the minimum-viable-profile gate -----------------------------------------


def test_gate_fails_below_threshold_with_exact_counts():
    watches = [w(4.0) for _ in range(14)] + [w(None) for _ in range(10)]  # 24 films, 14 rated
    result = check_gate(watches)
    assert result.ok is False
    assert result.films == 24
    assert result.rated == 14
    assert "24 film" in result.message and "14 rated" in result.message


def test_gate_passes_at_threshold():
    watches = [w(4.0) for _ in range(15)] + [w(None) for _ in range(10)]  # 25 films, 15 rated
    result = check_gate(watches)
    assert result.ok is True
    assert result.films == MIN_FILMS


# --- correlation signals -----------------------------------------------------


def test_contrarian_rates_against_the_crowd():
    # High TMDB score → low personal rating, and vice versa.
    votes = [8.5, 7.5, 6.5, 5.5, 4.5, 3.5]
    ratings = [1.0, 1.5, 2.5, 3.5, 4.5, 5.0]
    watches = [w(r, vote_average=v) for r, v in zip(ratings, votes)]
    ev = build_evidence(watches, now=NOW)
    assert ev["contrarianism"]["value"] < -0.8
    assert ev["contrarianism"]["n"] == 6


def test_mainstream_viewer_agrees_with_the_crowd():
    votes = [8.5, 7.5, 6.5, 5.5, 4.5, 3.5]
    ratings = [5.0, 4.5, 4.0, 3.0, 2.0, 1.0]
    watches = [w(r, vote_average=v) for r, v in zip(ratings, votes)]
    ev = build_evidence(watches, now=NOW)
    assert ev["contrarianism"]["value"] > 0.8


def test_slow_burn_lover_has_positive_patience():
    runtimes = [88, 95, 105, 150, 170, 185]
    ratings = [1.5, 2.0, 2.5, 4.0, 4.5, 5.0]
    watches = [w(r, runtime=rt) for r, rt in zip(ratings, runtimes)]
    ev = build_evidence(watches, now=NOW)
    assert ev["patience"]["value"] > 0.8


def test_obscurity_lover_negatively_correlates_with_vote_count():
    counts = [40, 120, 300, 40000, 90000, 150000]
    ratings = [5.0, 4.5, 4.0, 2.0, 1.5, 1.0]
    watches = [w(r, vote_count=c) for r, c in zip(ratings, counts)]
    ev = build_evidence(watches, now=NOW)
    assert ev["obscurity_preference"]["value"] < -0.8   # loves the obscure


# --- genre affinity is baseline-relative -------------------------------------


def test_dominant_genre_does_not_swamp_a_smaller_loved_one():
    drama = [w(3.0, genres=["Drama"]) for _ in range(10)]
    horror = [w(4.5, genres=["Horror"]) for _ in range(3)]
    ev = build_evidence(drama + horror, now=NOW)
    by_genre = {g["genre"]: g for g in ev["genre_affinity"]}
    # Drama dominates representation but Horror is the real preference.
    assert by_genre["Drama"]["share"] > by_genre["Horror"]["share"]
    assert by_genre["Horror"]["delta"] > 0
    assert by_genre["Drama"]["delta"] < 0
    assert "Horror" in ev["seeds"]["genres"]


# --- crew affinity respects the minimum sample size --------------------------


def test_crew_needs_min_sample_before_crowning_a_director():
    filler = [w(3.0) for _ in range(5)]
    denis = [w(4.5, crew={"director": ["Denis Villeneuve"]}) for _ in range(3)]  # n=3, above baseline
    one_hit = [w(5.0, crew={"director": ["One Hit Wonder"]})]                    # n=1, excluded
    ev = build_evidence(filler + denis + one_hit, now=NOW)
    directors = {d["name"] for d in ev["crew_affinity"]["director"]}
    assert "Denis Villeneuve" in directors
    assert "One Hit Wonder" not in directors


# --- rewatch + recency signals -----------------------------------------------


def test_rewatch_signal_surfaces_common_traits():
    watches = [
        w(5.0, is_rewatch=True, genres=["Horror"]),
        w(4.5, is_rewatch=True, genres=["Horror"]),
        w(4.0, is_rewatch=True, genres=["Thriller", "Horror"]),
        w(3.0, is_rewatch=False, genres=["Comedy"]),
    ]
    ev = build_evidence(watches, now=NOW)
    assert ev["rewatch_signal"]["count"] == 3
    assert ev["rewatch_signal"]["top_genres"][0] == "Horror"


def test_recency_drift_detects_a_rising_genre():
    recent = [w(4.0, genres=["Documentary"], watched_at=date(2026, 3, 1)) for _ in range(4)]
    older = [w(3.5, genres=["Action"], watched_at=date(2020, 1, 1)) for _ in range(8)]
    ev = build_evidence(recent + older, now=NOW)
    assert ev["recency_drift"]["recent_n"] == 4
    assert "Documentary" in ev["recency_drift"]["rising_genres"]


# --- degenerate inputs are safe ----------------------------------------------


def test_identical_ratings_give_undefined_correlations_not_nan():
    watches = [w(3.0, vote_average=v, runtime=rt) for v, rt in zip(range(5, 10), range(90, 190, 20))]
    ev = build_evidence(watches, now=NOW)
    assert ev["contrarianism"]["value"] is None       # zero variance → undefined, not a crash
    assert ev["patience"]["value"] is None
    assert ev["contrarianism"]["confidence"] == "insufficient"


def test_empty_input_does_not_crash():
    ev = build_evidence([], now=NOW)
    assert ev["counts"]["films"] == 0
    assert ev["baseline_rating"] is None
    assert ev["genre_affinity"] == []
    assert check_gate([]).ok is False


def test_missing_fields_are_excluded_from_their_signal():
    with_rt = [w(4.0, runtime=120) for _ in range(5)]
    without_rt = [w(4.0, runtime=None) for _ in range(3)]
    ev = build_evidence(with_rt + without_rt, now=NOW)
    assert ev["patience"]["n"] == 5   # only films that actually have a runtime


# --- DB adapters: produced and stored for a real profile ---------------------


def test_load_build_store_roundtrip():
    from app.db.session import SessionLocal
    from app.models.entities import Film, Profile, TasteProfile, WatchHistory
    from app.services.evidence import load_watches, store_evidence

    db = SessionLocal()
    try:
        db.add(Profile(handle="viewer"))
        f1 = Film(
            tmdb_id=1, media_type="film", title="A", release_year=1999, genres=["Drama"],
            runtime_minutes=120, tmdb_rating=7.0, tmdb_vote_count=1000, crew={"director": ["X"]},
        )
        f2 = Film(
            tmdb_id=2, media_type="film", title="B", release_year=2001, genres=["Horror"],
            runtime_minutes=95, tmdb_rating=6.0, tmdb_vote_count=500, crew={"director": ["Y"]},
        )
        db.add_all([f1, f2])
        db.commit()
        db.refresh(f1)
        db.refresh(f2)
        db.add(WatchHistory(profile_handle="viewer", film_id=f1.id, user_rating=4.0))
        db.add(WatchHistory(profile_handle="viewer", film_id=f2.id, user_rating=5.0, is_rewatch=True))
        db.commit()

        watches = load_watches(db, "viewer")
        assert len(watches) == 2

        ev = build_evidence(watches, now=NOW)
        assert ev["counts"]["films"] == 2
        assert ev["counts"]["rewatched"] == 1

        store_evidence(db, "viewer", ev, summary="draft")
        store_evidence(db, "viewer", ev, summary="draft")   # idempotent upsert
        rows = db.query(TasteProfile).filter_by(profile_handle="viewer").all()
        assert len(rows) == 1
        assert rows[0].evidence_json["counts"]["films"] == 2
    finally:
        db.close()

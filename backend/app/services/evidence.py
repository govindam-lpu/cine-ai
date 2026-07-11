"""The evidence layer — honest descriptive statistics about a viewer.

Pure Python, no model, no network. This is the archive's `profile.py` heuristics promoted from
"fake AI" to what they always were: statistics. The magic-number "pretension score" is replaced by
real correlations (contrarianism, obscurity, patience); the f-string "summary" is gone — writing is
the LLM's job (Phase 4). Every signal carries its sample size / confidence so downstream can
discount thin evidence.

The core is `build_evidence(watches)` over plain `WatchDatum` objects, so it's testable with
hand-built film sets. `load_watches` / `store_evidence` are the thin DB adapters.
"""

import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.models.entities import Film, TasteProfile, WatchHistory

# Minimum-viable-profile gate (PLAN.md §1a): enough films, and enough of them rated, to read taste.
MIN_FILMS = 25
MIN_RATED = 15

# A correlation needs at least this many usable points to mean anything.
_MIN_CORR_N = 5


@dataclass
class WatchDatum:
    """One watched film + the viewer's relationship to it. Decoupled from the ORM for testing."""

    rating: float | None
    is_rewatch: bool = False
    watched_at: date | None = None
    title: str = ""
    year: int | None = None
    genres: list[str] = field(default_factory=list)
    runtime: int | None = None
    vote_average: float | None = None
    vote_count: int | None = None
    crew: dict = field(default_factory=dict)
    language: str | None = None


@dataclass
class GateResult:
    ok: bool
    films: int
    rated: int
    message: str | None = None


def check_gate(watches: list[WatchDatum]) -> GateResult:
    films = len(watches)
    rated = sum(1 for w in watches if w.rating is not None)
    if films >= MIN_FILMS and rated >= MIN_RATED:
        return GateResult(ok=True, films=films, rated=rated)
    return GateResult(
        ok=False,
        films=films,
        rated=rated,
        message=(
            f"Cinerex needs at least {MIN_FILMS} films logged and {MIN_RATED} of them rated to read "
            f"your taste. Your export has {films} film{'s' if films != 1 else ''} "
            f"({rated} rated). Log a few more on Letterboxd and upload again."
        ),
    )


# --- small stats helpers -----------------------------------------------------


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    """Pearson correlation, or None when undefined (too few points / zero variance)."""
    n = len(xs)
    if n < _MIN_CORR_N:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:  # e.g. every film rated the same → correlation undefined, not NaN
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return round(sxy / math.sqrt(sxx * syy), 3)


def _confidence(n: int) -> str:
    if n < 8:
        return "low"
    if n < 25:
        return "medium"
    return "high"


def _signal(xs: list[float], ys: list[float]) -> dict:
    """Package a correlation with its sample size and confidence."""
    n = len(xs)
    value = _pearson(xs, ys)
    return {
        "value": value,
        "n": n,
        "confidence": _confidence(n) if value is not None else "insufficient",
    }


# --- the evidence bundle -----------------------------------------------------


def build_evidence(watches: list[WatchDatum], now: date | None = None) -> dict:
    """Compute the full evidence bundle. Never raises on degenerate input — returns neutral."""
    now = now or date.today()
    total = len(watches)
    rated = [w for w in watches if w.rating is not None]
    ratings = [w.rating for w in rated]
    baseline = round(sum(ratings) / len(ratings), 3) if ratings else None

    return {
        "counts": {
            "films": total,
            "rated": len(rated),
            "unrated": total - len(rated),
            "rewatched": sum(1 for w in watches if w.is_rewatch),
        },
        "baseline_rating": baseline,
        "rating_std": round(statistics.pstdev(ratings), 3) if len(ratings) > 1 else 0.0,
        "genre_affinity": _bucket_affinity(watches, lambda w: w.genres, baseline, "genre"),
        "era_affinity": _bucket_affinity(watches, _decade_keys, baseline, "decade"),
        "crew_affinity": _crew_affinity(rated, baseline),
        "contrarianism": _correlation_over(rated, lambda w: w.vote_average),
        "obscurity_preference": _correlation_over(
            rated, lambda w: math.log10(w.vote_count) if w.vote_count and w.vote_count > 0 else None
        ),
        "patience": _correlation_over(rated, lambda w: float(w.runtime) if w.runtime else None),
        "rewatch_signal": _rewatch_signal(watches),
        "recency_drift": _recency_drift(watches, now),
        "languages": _languages(watches),
        "seeds": _seeds(watches, baseline),
    }


def _decade_keys(w: WatchDatum) -> list[str]:
    return [f"{(w.year // 10) * 10}s"] if w.year else []


def _bucket_affinity(watches, key_fn, baseline, label) -> list[dict]:
    """Per bucket (genre / decade): representation share + mean rating vs the personal baseline.

    Baseline-relative, so a dominant genre doesn't automatically read as a *preference* — a viewer
    can watch mostly Drama yet rate their rare Westerns higher."""
    all_counts: Counter = Counter()
    rated_sums: defaultdict = defaultdict(float)
    rated_counts: Counter = Counter()

    for w in watches:
        for key in key_fn(w):
            all_counts[key] += 1
            if w.rating is not None:
                rated_sums[key] += w.rating
                rated_counts[key] += 1

    out = []
    for key, count in all_counts.items():
        rc = rated_counts[key]
        mean = rated_sums[key] / rc if rc else None
        delta = round(mean - baseline, 3) if (mean is not None and baseline is not None) else None
        out.append(
            {
                label: key,
                "n": rc,
                "share": round(count / len(watches), 3) if watches else 0.0,
                "mean_rating": round(mean, 3) if mean is not None else None,
                "delta": delta,
            }
        )
    out.sort(key=lambda d: (d["n"], d["share"]), reverse=True)
    return out


def _crew_affinity(rated: list[WatchDatum], baseline: float | None, min_n: int = 3) -> dict:
    """Directors/cinematographers/composers the viewer rates above baseline, min sample size so
    one 5-star film doesn't crown someone."""
    roles = ("director", "cinematographer", "composer")
    result: dict[str, list[dict]] = {role: [] for role in roles}
    if baseline is None:
        return result

    for role in roles:
        sums: defaultdict = defaultdict(float)
        counts: Counter = Counter()
        for w in rated:
            for name in (w.crew or {}).get(role, []) or []:
                sums[name] += w.rating
                counts[name] += 1
        items = []
        for name, cnt in counts.items():
            if cnt >= min_n:
                mean = sums[name] / cnt
                delta = round(mean - baseline, 3)
                if delta > 0:  # "rated above baseline"
                    items.append({"name": name, "n": cnt, "mean_rating": round(mean, 3), "delta": delta})
        items.sort(key=lambda i: (i["delta"], i["n"]), reverse=True)
        result[role] = items[:8]
    return result


def _correlation_over(rated: list[WatchDatum], value_fn) -> dict:
    xs: list[float] = []
    ys: list[float] = []
    for w in rated:
        y = value_fn(w)
        if y is not None:
            xs.append(w.rating)
            ys.append(y)
    return _signal(xs, ys)


def _rewatch_signal(watches: list[WatchDatum]) -> dict:
    rewatched = [w for w in watches if w.is_rewatch]
    genres: Counter = Counter()
    directors: Counter = Counter()
    for w in rewatched:
        for g in w.genres or []:
            genres[g] += 1
        for d in (w.crew or {}).get("director", []) or []:
            directors[d] += 1
    return {
        "count": len(rewatched),
        "top_genres": [g for g, _ in genres.most_common(5)],
        "top_directors": [d for d, _ in directors.most_common(5)],
    }


def _recency_drift(watches: list[WatchDatum], now: date) -> dict:
    dated = [w for w in watches if w.watched_at]
    if not dated:
        return {"recent_n": 0, "recent_top_genres": [], "lifetime_top_genres": [], "rising_genres": []}

    recent = [w for w in dated if 0 <= (now - w.watched_at).days <= 365]

    def genre_shares(ws):
        counter: Counter = Counter()
        total = 0
        for w in ws:
            for g in w.genres or []:
                counter[g] += 1
                total += 1
        shares = {g: c / total for g, c in counter.items()} if total else {}
        return shares, [g for g, _ in counter.most_common(5)]

    recent_shares, recent_top = genre_shares(recent)
    life_shares, life_top = genre_shares(dated)
    rising = [
        g for g, s in recent_shares.items() if s >= life_shares.get(g, 0.0) + 0.08
    ]
    rising.sort(key=lambda g: recent_shares[g] - life_shares.get(g, 0.0), reverse=True)
    return {
        "recent_n": len(recent),
        "recent_top_genres": recent_top,
        "lifetime_top_genres": life_top,
        "rising_genres": rising[:5],
    }


def _languages(watches: list[WatchDatum]) -> list[dict]:
    counts = Counter(w.language for w in watches if w.language)
    total = len(watches) or 1
    return [
        {"language": lang, "n": count, "share": round(count / total, 3)}
        for lang, count in counts.most_common()
    ]


def _seeds(watches: list[WatchDatum], baseline: float | None) -> dict:
    """Top genres/decades/languages to seed TMDB discovery in the ranker (Phase 3)."""
    genres = _bucket_affinity(watches, lambda w: w.genres, baseline, "genre")
    eras = _bucket_affinity(watches, _decade_keys, baseline, "decade")

    liked = [g for g in genres if (g["delta"] or 0) > 0 and g["n"] >= 2]
    liked.sort(key=lambda d: d["delta"], reverse=True)
    seed_genres = [g["genre"] for g in liked[:4]] or [g["genre"] for g in genres[:3]]

    seed_decades = [e["decade"] for e in eras if (e["delta"] or 0) >= 0][:3] or [
        e["decade"] for e in eras[:2]
    ]
    seed_languages = [lang["language"] for lang in _languages(watches)[:2]]
    return {"genres": seed_genres, "decades": seed_decades, "languages": seed_languages}


# --- DB adapters -------------------------------------------------------------


def load_watches(db: Session, handle: str) -> list[WatchDatum]:
    rows = (
        db.query(WatchHistory, Film)
        .join(Film, WatchHistory.film_id == Film.id)
        .filter(WatchHistory.profile_handle == handle)
        .all()
    )
    return [
        WatchDatum(
            rating=wh.user_rating,
            is_rewatch=wh.is_rewatch,
            watched_at=wh.watched_at,
            title=film.title,
            year=film.release_year,
            genres=film.genres or [],
            runtime=film.runtime_minutes,
            vote_average=film.tmdb_rating,
            vote_count=film.tmdb_vote_count,
            crew=film.crew or {},
            language=film.original_language,
        )
        for wh, film in rows
    ]


def store_evidence(db: Session, handle: str, evidence: dict, summary: str | None = None) -> TasteProfile:
    tp = db.query(TasteProfile).filter_by(profile_handle=handle).first()
    if tp is None:
        tp = TasteProfile(profile_handle=handle, evidence_json=evidence, summary=summary)
        db.add(tp)
    else:
        tp.evidence_json = evidence
        if summary is not None:
            tp.summary = summary
    db.commit()
    db.refresh(tp)
    return tp

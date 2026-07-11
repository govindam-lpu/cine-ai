"""The ranker — content-based, embedding-driven, CPU-only. The product's core.

Given the evidence and TMDB candidates, produce the top N films the user hasn't seen, each with the
structured `signals` that made it score — so the writer (Phase 4) never has to guess why a film was
picked. The ranker explains itself.

The similarity backbone is cosine to a taste vector (rating-weighted embeddings), tilted by the
evidence signals (director affinity, genre/era affinity, obscurity, patience). Watched films are
filtered out in Python before scoring — a hard invariant, never delegated to TMDB.

Pure functions (build_taste_vector / score_candidate / rank_candidates / evaluate_ranking) carry the
logic and are tested without the network; `recommend` is the IO orchestrator.
"""

import logging
import math
import random
from dataclasses import dataclass, field

import numpy as np
from sqlalchemy.orm import Session

from app.models.entities import Film, WatchHistory
from app.services.embeddings import EMBED_DIM, embed_texts, film_embedding_text
from app.services.enrich import EnrichmentService
from app.services.tmdb import TMDBService

logger = logging.getLogger(__name__)

# Hand-set starting weights (PLAN.md §1c: "weights start hand-set and get tuned"). Cosine is the
# backbone; the rest tilt. Kept small so similarity dominates and evidence nudges.
WEIGHTS = {
    "cosine": 1.0,
    "director": 0.25,
    "genre": 0.15,
    "era": 0.08,
    "obscurity": 0.15,
    "patience": 0.10,
}

# TMDB movie genre ids (stable list) — discover needs ids, evidence speaks names.
GENRE_NAME_TO_ID = {
    "Action": 28, "Adventure": 12, "Animation": 16, "Comedy": 35, "Crime": 80,
    "Documentary": 99, "Drama": 18, "Family": 10751, "Fantasy": 14, "History": 36,
    "Horror": 27, "Music": 10402, "Mystery": 9648, "Romance": 10749,
    "Science Fiction": 878, "TV Movie": 10770, "Thriller": 53, "War": 10752, "Western": 37,
}

# Mood → genres it biases discovery toward (folded into the seed genres when a mood is set).
MOOD_GENRES = {
    "uplifting": ["Comedy", "Adventure", "Family", "Music"],
    "dark": ["Crime", "Horror", "Thriller", "War"],
    "cerebral": ["Science Fiction", "Mystery", "Documentary", "Drama"],
    "cozy": ["Romance", "Comedy", "Family", "Animation"],
    "tense": ["Thriller", "Horror", "Crime", "Mystery"],
}


@dataclass
class FilmVector:
    """A candidate/film decoupled from the ORM, so ranking is testable without a DB."""

    tmdb_id: int
    title: str
    embedding: np.ndarray | None
    genres: list[str] = field(default_factory=list)
    release_year: int | None = None
    runtime: int | None = None
    vote_count: int | None = None
    crew: dict = field(default_factory=dict)
    overview: str | None = None
    poster_path: str | None = None


@dataclass
class Recommendation:
    tmdb_id: int
    title: str
    score: float
    similarity: float
    signals: list[dict]
    vector: FilmVector


def film_to_vector(film: Film) -> FilmVector:
    return FilmVector(
        tmdb_id=film.tmdb_id,
        title=film.title,
        embedding=np.asarray(film.embedding, dtype=np.float32) if film.embedding else None,
        genres=film.genres or [],
        release_year=film.release_year,
        runtime=film.runtime_minutes,
        vote_count=film.tmdb_vote_count,
        crew=film.crew or {},
        overview=film.overview,
        poster_path=film.poster_path,
    )


def ensure_film_embeddings(db: Session, films: list[Film]) -> int:
    """Embed (and cache on Film.embedding) any films that don't have one yet. Returns count embedded.

    Cold films with nothing to embed are skipped, not crashed on. Cached rows are never re-embedded.
    """
    texts: list[str] = []
    targets: list[Film] = []
    for film in films:
        if film.embedding:
            continue
        text = film_embedding_text(film.overview, film.genres, film.keywords)
        if text is None:
            continue
        texts.append(text)
        targets.append(film)

    if not texts:
        return 0

    vectors = embed_texts(texts)
    for film, vector in zip(targets, vectors):
        film.embedding = vector.tolist()
    db.commit()
    return len(targets)


# --- taste vector ------------------------------------------------------------


def build_taste_vector(rated: list[tuple[np.ndarray, float]], baseline: float | None) -> np.ndarray | None:
    """Rating-weighted mean of liked embeddings minus disliked — the viewer's positive space with
    their negative space subtracted. Weight each film by how far its rating sits from the baseline.

    Returns a unit vector, or None if there's nothing usable (e.g. every film rated identically and
    no fallback signal)."""
    if not rated:
        return None
    if baseline is None:
        baseline = sum(r for _, r in rated) / len(rated)

    acc = np.zeros(EMBED_DIM, dtype=np.float32)
    weight_mass = 0.0
    for emb, rating in rated:
        w = rating - baseline
        acc += w * emb
        weight_mass += abs(w)

    norm = float(np.linalg.norm(acc))
    if weight_mass == 0.0 or norm == 0.0:
        # Everything rated the same → no positive/negative separation. Fall back to the centroid of
        # what they watched (their general region of taste).
        centroid = np.mean([emb for emb, _ in rated], axis=0)
        norm = float(np.linalg.norm(centroid))
        if norm == 0.0:
            return None
        return centroid / norm
    return acc / norm


# --- scoring -----------------------------------------------------------------


def _clamp(value: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def score_candidate(cand: FilmVector, taste: np.ndarray, evidence: dict) -> tuple[float, float, list[dict]]:
    """Score one candidate; return (score, cosine_similarity, fired-signals).

    Signals are the structured "why it scored" the writer consumes — each names a concrete fact.
    """
    signals: list[dict] = []

    similarity = float(cand.embedding @ taste) if cand.embedding is not None else 0.0
    score = WEIGHTS["cosine"] * similarity
    signals.append(
        {"factor": "similarity", "strength": round(similarity, 3),
         "detail": "It sits close to the center of what you rate highly."}
    )

    # Director affinity — a director the viewer rates above their baseline.
    dir_deltas = {d["name"]: d["delta"] for d in evidence.get("crew_affinity", {}).get("director", [])}
    for name in cand.crew.get("director", []) or []:
        if name in dir_deltas:
            bonus = WEIGHTS["director"] * _clamp(dir_deltas[name], 0, 1)
            score += bonus
            signals.append(
                {"factor": "director", "strength": round(bonus, 3),
                 "detail": f"You rate {name}'s films above your average.", "name": name}
            )
            break

    # Genre affinity — overlap with the viewer's above-baseline genres.
    genre_deltas = {g["genre"]: g["delta"] for g in evidence.get("genre_affinity", []) if (g.get("delta") or 0) > 0}
    matched = [g for g in cand.genres if g in genre_deltas]
    if matched:
        strongest = max(matched, key=lambda g: genre_deltas[g])
        bonus = WEIGHTS["genre"] * _clamp(genre_deltas[strongest], 0, 1)
        score += bonus
        signals.append(
            {"factor": "genre", "strength": round(bonus, 3),
             "detail": f"{strongest} is one of your higher-rated genres.", "name": strongest}
        )

    # Era affinity — the candidate's decade is one the viewer rates up.
    pos_decades = {e["decade"] for e in evidence.get("era_affinity", []) if (e.get("delta") or 0) > 0}
    if cand.release_year:
        decade = f"{(cand.release_year // 10) * 10}s"
        if decade in pos_decades:
            score += WEIGHTS["era"]
            signals.append(
                {"factor": "era", "strength": round(WEIGHTS["era"], 3),
                 "detail": f"You rate {decade} films highly.", "name": decade}
            )

    # Obscurity match — align vote_count with the viewer's obscurity preference.
    obsc = evidence.get("obscurity_preference", {}).get("value")
    if obsc is not None and cand.vote_count:
        obscurity_of_cand = _clamp((3.5 - math.log10(cand.vote_count + 1)) / 2.5)  # +1 obscure, -1 popular
        contribution = WEIGHTS["obscurity"] * (-obsc) * obscurity_of_cand
        if abs(contribution) > 0.01:
            score += contribution
            if contribution > 0:
                phrasing = "It's the kind of under-the-radar film you gravitate to." if obsc < 0 \
                    else "It has the broad audience you tend to rate well."
                signals.append({"factor": "obscurity", "strength": round(contribution, 3), "detail": phrasing})

    # Patience match — align runtime with the viewer's patience.
    patience = evidence.get("patience", {}).get("value")
    if patience is not None and cand.runtime:
        runtime_of_cand = _clamp((cand.runtime - 110) / 50.0)  # +1 long, -1 short
        contribution = WEIGHTS["patience"] * patience * runtime_of_cand
        if abs(contribution) > 0.01:
            score += contribution
            if contribution > 0:
                phrasing = "It takes its time, the way the films you rate highly do." if patience > 0 \
                    else "It's tight and quick, matching your rated favorites."
                signals.append({"factor": "patience", "strength": round(contribution, 3), "detail": phrasing})

    signals.sort(key=lambda s: s["strength"], reverse=True)
    return score, similarity, signals


def rank_candidates(
    taste: np.ndarray,
    candidates: list[FilmVector],
    watched_ids: set[int],
    evidence: dict,
    limit: int = 8,
) -> list[Recommendation]:
    """Score all candidates, exclude watched (hard invariant), return the top `limit`."""
    seen: set[int] = set()
    ranked: list[Recommendation] = []
    for cand in candidates:
        if cand.tmdb_id in watched_ids or cand.tmdb_id in seen:
            continue
        if cand.embedding is None:
            continue  # can't place a film we couldn't embed
        seen.add(cand.tmdb_id)
        score, similarity, signals = score_candidate(cand, taste, evidence)
        ranked.append(
            Recommendation(
                tmdb_id=cand.tmdb_id, title=cand.title, score=round(score, 4),
                similarity=round(similarity, 4), signals=signals, vector=cand,
            )
        )
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked[:limit]


# --- candidate discovery (IO) ------------------------------------------------


def discover_candidate_ids(
    tmdb: TMDBService, evidence: dict, watched_ids: set[int], mood: str | None = None, target: int = 60
) -> list[int]:
    """Pull ~`target` candidate TMDB ids via discover, seeded by the evidence. Widen (relax filters)
    rather than return too few; watched ids are filtered here too (before scoring)."""
    seeds = evidence.get("seeds", {})
    genre_names = list(seeds.get("genres", []))
    if mood and mood in MOOD_GENRES:
        genre_names = MOOD_GENRES[mood] + [g for g in genre_names if g not in MOOD_GENRES[mood]]
    genre_ids = [GENRE_NAME_TO_ID[g] for g in genre_names if g in GENRE_NAME_TO_ID]

    ids: list[int] = []
    seen: set[int] = set()

    def pull(params: dict, pages: int = 2) -> None:
        for page in range(1, pages + 1):
            data = tmdb.discover_movies({**params, "page": page})
            results = data.get("results", [])
            if not results:
                break
            for r in results:
                tid = r.get("id")
                if not tid or tid in watched_ids or tid in seen:
                    continue
                seen.add(tid)
                ids.append(tid)
            if len(ids) >= target:
                return

    # Quality, not popularity: vote_average.desc with a real vote floor surfaces well-regarded films
    # in the viewer's genres (foreign/arthouse included). No language hard-filter — it excluded the
    # world cinema an arthouse viewer loves. Similarity + the evidence signals then personalize.
    quality = {"sort_by": "vote_average.desc", "vote_count.gte": 200, "include_adult": "false"}

    # One pull per preferred genre → each preferred genre gets representation in the pool.
    for gid in genre_ids[:4]:
        if len(ids) >= target:
            break
        pull({**quality, "with_genres": str(gid)})

    if len(ids) < target and genre_ids:
        pull({**quality, "with_genres": "|".join(str(g) for g in genre_ids[:4])}, pages=3)

    if len(ids) < target:
        logger.info("ranker: widening discovery (dropping genre filter)")
        pull({"sort_by": "vote_average.desc", "vote_count.gte": 500, "include_adult": "false"}, pages=3)

    return ids[:target]


def recommend(
    db: Session,
    handle: str,
    evidence: dict,
    tmdb: TMDBService | None = None,
    mood: str | None = None,
    limit: int = 8,
    candidate_pool: int = 60,
) -> list[Recommendation]:
    """Full pipeline: taste vector from the viewer's films → TMDB candidates → score → top `limit`."""
    tmdb = tmdb or TMDBService()

    rows = (
        db.query(WatchHistory, Film)
        .join(Film, WatchHistory.film_id == Film.id)
        .filter(WatchHistory.profile_handle == handle)
        .all()
    )
    user_films = [film for _, film in rows]
    ensure_film_embeddings(db, user_films)

    rated = [
        (np.asarray(film.embedding, dtype=np.float32), wh.user_rating)
        for wh, film in rows
        if wh.user_rating is not None and film.embedding
    ]
    taste = build_taste_vector(rated, evidence.get("baseline_rating"))
    if taste is None:
        return []

    watched_ids = {film.tmdb_id for film in user_films if film.tmdb_id}

    candidate_ids = discover_candidate_ids(tmdb, evidence, watched_ids, mood, candidate_pool)
    svc = EnrichmentService(tmdb)
    candidate_films: list[Film] = []
    for tid in candidate_ids:
        film = svc.get_or_create_by_tmdb_id(db, tid)
        if film:
            candidate_films.append(film)

    # Resilience: if discovery came back thin (niche taste, or TMDB unavailable), supplement from
    # already-enriched, unwatched films in the cache rather than returning fewer than asked.
    if len(candidate_films) < limit:
        have = {f.tmdb_id for f in candidate_films}
        cached = (
            db.query(Film)
            .filter(Film.embedding.isnot(None))
            .limit(candidate_pool * 3)
            .all()
        )
        for film in cached:
            if film.tmdb_id and film.tmdb_id not in watched_ids and film.tmdb_id not in have:
                candidate_films.append(film)
                have.add(film.tmdb_id)
        if candidate_ids and len(candidate_films) > len(candidate_ids):
            logger.info("ranker: supplemented discovery with %d cached films", len(candidate_films) - len(candidate_ids))

    ensure_film_embeddings(db, candidate_films)

    vectors = [film_to_vector(f) for f in candidate_films if f.tmdb_id not in watched_ids]
    return rank_candidates(taste, vectors, watched_ids, evidence, limit)


# --- evaluation --------------------------------------------------------------


def _pairwise_auc(scored: list[tuple[float, float]], min_gap: float) -> tuple[float | None, int]:
    """AUC over rating pairs at least `min_gap` apart: fraction the score orders correctly."""
    pairs = 0.0
    correct = 0.0
    for si, ri in scored:
        for sj, rj in scored:
            if ri - rj >= min_gap:
                pairs += 1
                if si > sj:
                    correct += 1
                elif si == sj:
                    correct += 0.5
    if not pairs:
        return None, 0
    return round(correct / pairs, 3), int(pairs)


def evaluate_ranking(
    rated: list[tuple[np.ndarray, float]], holdout_frac: float = 0.2, seed: int = 0, min_gap: float = 1.0
) -> dict:
    """Hold out a fraction of the viewer's rated films, build the taste vector from the rest, and
    measure whether held-out films they rated clearly higher score above films they rated clearly
    lower (pairwise AUC). AUC 0.5 == random; the ranker must clear that by a clear margin.

    Headline `auc` counts only pairs at least `min_gap` stars apart — a content-based ranker's job
    is to separate loved from disliked ("put 4.5s above 2s"), not to resolve 4.0-vs-4.5 noise that
    overview-embeddings can't. `auc_all` (every pair) is reported alongside for transparency.
    """
    if len(rated) < 5:
        return {"auc": None, "held": 0, "train": len(rated), "reason": "too few rated films"}

    rng = random.Random(seed)
    order = list(range(len(rated)))
    rng.shuffle(order)
    n_hold = max(2, int(round(len(rated) * holdout_frac)))
    hold_idx = set(order[:n_hold])

    train = [rated[i] for i in order if i not in hold_idx]
    held = [rated[i] for i in order if i in hold_idx]
    baseline = sum(r for _, r in train) / len(train)
    taste = build_taste_vector(train, baseline)
    if taste is None:
        return {"auc": None, "held": len(held), "train": len(train), "reason": "no taste vector"}

    scored = [(float(emb @ taste), rating) for emb, rating in held]
    auc, pairs = _pairwise_auc(scored, min_gap)
    auc_all, _ = _pairwise_auc(scored, 0.01)
    return {
        "auc": auc, "auc_all": auc_all, "held": len(held), "train": len(train), "pairs": pairs,
    }

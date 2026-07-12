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
import threading
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

# Prompt mode: when the user types a request, the request LEADS and taste only personalizes within
# it. request-fit (embedding + requested-genre overlap) dominates; taste is a light tie-break; the
# taste-content bonuses (genre/era/obscurity/patience) are OFF — they encode the taste the user is
# explicitly overriding, and were dragging off-request films (e.g. dramas for "romantic comedy") up.
PROMPT_W = {"sim": 1.8, "genre": 1.0, "taste": 0.25, "director": 0.2, "quality": 0.35}
_PROMPT_MIN_RATING = 6.0  # floor for the request pool, so search never returns poorly-rated films
_GENRE_FIT_BASE = 0.44  # a genre counts toward "what you asked for" only above this prompt-similarity
_STRONG_GENRE = 0.50    # a genre this close to the request counts as "strongly requested"
# Dark/violent genres: if the request doesn't ask for them, keep them out of the pool — so
# "a feel-good comedy" can't surface a Comedy-tagged thriller like Parasite.
DARK_GENRES = ["Horror", "War", "Crime", "Thriller"]

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

# Genre-name embeddings, computed once, for mapping a free-text prompt to TMDB genres in embedding
# space (no LLM — constraint 2). Lets "something scary and tense" seed discovery with Horror/Thriller.
_GENRE_EMB: list[tuple[str, np.ndarray]] | None = None
_GENRE_EMB_LOCK = threading.Lock()


def _genre_embeddings() -> list[tuple[str, np.ndarray]]:
    global _GENRE_EMB
    if _GENRE_EMB is None:
        with _GENRE_EMB_LOCK:
            if _GENRE_EMB is None:
                names = list(GENRE_NAME_TO_ID.keys())
                vectors = embed_texts([f"A {name} film" for name in names])
                _GENRE_EMB = list(zip(names, vectors))
    return _GENRE_EMB


def prompt_genre_scores(prompt_vec: np.ndarray) -> list[tuple[str, float]]:
    """Every TMDB genre ranked by similarity to the prompt vector (best first)."""
    return sorted(
        ((name, float(prompt_vec @ vec)) for name, vec in _genre_embeddings()),
        key=lambda x: x[1],
        reverse=True,
    )


def genres_for_prompt(prompt_vec: np.ndarray, top_k: int = 4, threshold: float = 0.42) -> list[str]:
    """The TMDB genres nearest a prompt vector (best first) — used to seed discovery so the candidate
    pool actually contains what the user asked for. Empty if nothing clears the bar (then discovery
    falls back to the evidence seeds, and the prompt still tilts scoring)."""
    return [name for name, sim in prompt_genre_scores(prompt_vec)[:top_k] if sim >= threshold]


def prompt_genre_weights(prompt_vec: np.ndarray, top_k: int = 3) -> dict[str, float]:
    """Positive 'fit to the request' weight per genre — how much a candidate tagged with it counts
    as matching what the user asked for. Only genres clearly above the base similarity qualify."""
    return {
        name: sim - _GENRE_FIT_BASE
        for name, sim in prompt_genre_scores(prompt_vec)[:top_k]
        if sim > _GENRE_FIT_BASE
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
    tmdb_rating: float | None = None


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
        tmdb_rating=film.tmdb_rating,
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


def score_candidate(
    cand: FilmVector,
    taste: np.ndarray,
    evidence: dict,
    prompt_vec: np.ndarray | None = None,
    prompt_text: str | None = None,
    prompt_genre_wts: dict[str, float] | None = None,
) -> tuple[float, float, list[dict]]:
    """Score one candidate; return (score, taste_similarity, fired-signals).

    Signals are the structured "why it scored" the writer consumes — each names a concrete fact.
    Two modes: a free-text request switches on PROMPT MODE (the request leads, taste personalizes);
    otherwise TASTE MODE (the taste vector leads, evidence tilts).
    """
    taste_sim = float(cand.embedding @ taste) if cand.embedding is not None else 0.0

    if prompt_vec is not None and cand.embedding is not None:
        return _score_prompt_mode(cand, taste_sim, evidence, prompt_vec, prompt_text, prompt_genre_wts or {})

    signals: list[dict] = []
    score = WEIGHTS["cosine"] * taste_sim
    signals.append(
        {"factor": "similarity", "strength": round(taste_sim, 3),
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
    return score, taste_sim, signals


def _score_prompt_mode(
    cand: FilmVector,
    taste_sim: float,
    evidence: dict,
    prompt_vec: np.ndarray,
    prompt_text: str | None,
    genre_wts: dict[str, float],
) -> tuple[float, float, list[dict]]:
    """The request leads: request-fit (embedding + requested-genre overlap) dominates, taste is a
    light personalizer, and the taste-content bonuses are off. This is what stops a 'romantic comedy'
    request from returning the viewer's beloved dramas."""
    signals: list[dict] = []
    prompt_sim = float(cand.embedding @ prompt_vec)

    matched = [g for g in (cand.genres or []) if g in genre_wts]
    genre_fit = sum(genre_wts[g] for g in matched)

    score = (
        PROMPT_W["sim"] * prompt_sim
        + PROMPT_W["genre"] * genre_fit
        + PROMPT_W["taste"] * taste_sim
    )
    # Quality nudge — prefer well-regarded films within the request (recommendations should be good).
    if cand.tmdb_rating is not None:
        score += PROMPT_W["quality"] * _clamp((cand.tmdb_rating - 6.5) / 2.0)

    detail = (
        f'It fits what you asked for: "{prompt_text}".' if prompt_text else "It fits the mood you asked for."
    )
    signals.append(
        {"factor": "prompt", "strength": round(PROMPT_W["sim"] * prompt_sim, 3),
         "detail": detail, "name": "your request"}
    )
    if matched:
        best = max(matched, key=lambda g: genre_wts[g])
        signals.append(
            {"factor": "genre", "strength": round(PROMPT_W["genre"] * genre_fit, 3),
             "detail": f"It's {best.lower()} — the kind of film you asked for.", "name": best}
        )

    # Light director personalization — only fires on a director the viewer already rates up, so it
    # sharpens the pick within the request without pulling in off-request films.
    dir_deltas = {d["name"]: d["delta"] for d in evidence.get("crew_affinity", {}).get("director", [])}
    for name in cand.crew.get("director", []) or []:
        if name in dir_deltas:
            bonus = PROMPT_W["director"] * _clamp(dir_deltas[name], 0, 1)
            score += bonus
            signals.append(
                {"factor": "director", "strength": round(bonus, 3),
                 "detail": f"You rate {name}'s films above your average.", "name": name}
            )
            break

    signals.sort(key=lambda s: s["strength"], reverse=True)
    return score, taste_sim, signals


def rank_candidates(
    taste: np.ndarray,
    candidates: list[FilmVector],
    watched_ids: set[int],
    evidence: dict,
    limit: int = 8,
    prompt_vec: np.ndarray | None = None,
    prompt_text: str | None = None,
    prompt_genre_wts: dict[str, float] | None = None,
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
        score, similarity, signals = score_candidate(
            cand, taste, evidence, prompt_vec, prompt_text, prompt_genre_wts
        )
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
    tmdb: TMDBService,
    evidence: dict,
    watched_ids: set[int],
    mood: str | None = None,
    target: int = 60,
    prompt_genres: list[str] | None = None,
    and_genres: list[str] | None = None,
    exclude_genres: list[str] | None = None,
    keyword_ids: list[int] | None = None,
    min_rating: float | None = None,
) -> list[int]:
    """Pull ~`target` candidate TMDB ids via discover. Widen (relax filters) rather than return too
    few; watched ids are filtered here too (before scoring)."""
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

    if mood and mood in MOOD_GENRES:
        prompt_genres = MOOD_GENRES[mood] + [g for g in (prompt_genres or []) if g not in MOOD_GENRES[mood]]

    # PROMPT MODE: the pool comes from the *requested* genres, not the viewer's taste seeds — so a
    # "romantic comedy" request can't surface their beloved crime dramas. Tiered so the purest
    # matches (tagged with BOTH strongly-requested genres) lead, then broaden only as needed.
    if prompt_genres:
        pg_ids = [GENRE_NAME_TO_ID[g] for g in prompt_genres if g in GENRE_NAME_TO_ID]
        and_ids = [GENRE_NAME_TO_ID[g] for g in (and_genres or []) if g in GENRE_NAME_TO_ID]
        quality = {
            "sort_by": "vote_average.desc", "vote_count.gte": 120, "include_adult": "false",
            "vote_average.gte": max(_PROMPT_MIN_RATING, min_rating or 0),  # never surface bad films
        }
        # Keep non-narrative content (standup/concert specials, music videos, TV movies) and the
        # genres the request rules out (from the parsed intent, or the DARK_GENRES fallback) out of
        # the pool. A genre the user actually asked for is never excluded.
        non_narrative = ["Documentary", "Music", "TV Movie"]
        excl = {
            GENRE_NAME_TO_ID[g]
            for g in (non_narrative + list(exclude_genres or []))
            if g in GENRE_NAME_TO_ID and g not in prompt_genres
        }
        if excl:
            quality["without_genres"] = ",".join(str(i) for i in sorted(excl))
        # Precision first: films tagged with the requested theme keywords (feel-good, heist, …) lead.
        if keyword_ids:
            pull({**quality, "with_keywords": "|".join(str(k) for k in keyword_ids)}, pages=2)
        if len(and_ids) >= 2:
            pull({**quality, "with_genres": f"{and_ids[0]},{and_ids[1]}"}, pages=3)   # AND — purest
        if len(ids) < target and pg_ids:
            pull({**quality, "with_genres": "|".join(str(g) for g in pg_ids)}, pages=4)  # OR
        for gid in pg_ids:
            if len(ids) >= target:
                break
            pull({**quality, "with_genres": str(gid)})
        if len(ids) < 12:  # genuinely thin (a niche genre) → broaden on quality alone
            logger.info("ranker: prompt pool thin, broadening on rating")
            pull({"sort_by": "vote_average.desc", "vote_count.gte": 300, "include_adult": "false"}, pages=2)
        return ids[:target]

    # TASTE MODE: seed from the evidence's top genres.
    genre_ids = [GENRE_NAME_TO_ID[g] for g in evidence.get("seeds", {}).get("genres", []) if g in GENRE_NAME_TO_ID]

    # Quality, not popularity: vote_average.desc with a real vote floor surfaces well-regarded films
    # in the viewer's genres (foreign/arthouse included). No language hard-filter — it excluded the
    # world cinema an arthouse viewer loves. Similarity + the evidence signals then personalize.
    quality = {"sort_by": "vote_average.desc", "vote_count.gte": 200, "include_adult": "false"}

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


def _film_hits_terms(film: Film, terms: list[str]) -> bool:
    """True if any excluded term appears in the film's own description — the reliable filter for
    non-narrative/off-tone content (standup, concert, tragedy) that genre tags miss."""
    hay = ((film.overview or "") + " " + " ".join(film.keywords or [])).lower()
    return any(term in hay for term in terms)


def _build_search_plan(prompt_text: str, intent: dict | None, tmdb: TMDBService) -> dict | None:
    """Turn a request into an executable search plan: a vector to rank by, the genres to pull and to
    exclude, theme-keyword ids, and terms to filter out. From the parsed LLM intent when present,
    else derived from the embedding alone (fallback). Never raises — None means 'rank by taste'."""
    try:
        if intent:
            query = (intent.get("query") or prompt_text).strip() or prompt_text
            genres = [g for g in intent.get("genres", []) if g in GENRE_NAME_TO_ID][:3]
            exclude_genres = [g for g in intent.get("exclude_genres", []) if g in GENRE_NAME_TO_ID]
            exclude_terms = [t.strip().lower() for t in intent.get("exclude_terms", []) if t and t.strip()]
            keyword_ids = tmdb.search_keyword_ids(list(intent.get("keywords", []))[:4])
            min_rating = intent.get("min_rating")
        else:
            query = prompt_text
            key = prompt_text.lower()
            if key in MOOD_GENRES:
                genres = list(MOOD_GENRES[key])
            else:
                scores = prompt_genre_scores(embed_texts([prompt_text])[0])
                strong = [g for g, s in scores if s >= _STRONG_GENRE]
                genres = strong[:3] if strong else [scores[0][0]]
            exclude_genres = [g for g in DARK_GENRES if g not in genres]
            exclude_terms = ["stand-up", "concert", "live performance"]
            keyword_ids = []
            min_rating = None

        prompt_vec = embed_texts([query])[0]
        return {
            "vec": prompt_vec,
            "text": prompt_text,                       # the user's own words, for the "why" signal
            "genres": genres,
            "and_genres": genres if len(genres) == 2 else [],
            "exclude_genres": exclude_genres,
            "keyword_ids": keyword_ids,
            "exclude_terms": exclude_terms,
            "min_rating": min_rating,
            "gwts": prompt_genre_weights(prompt_vec),
        }
    except Exception:  # noqa: BLE001
        return None


def recommend(
    db: Session,
    handle: str,
    evidence: dict,
    tmdb: TMDBService | None = None,
    mood: str | None = None,
    prompt: str | None = None,
    intent: dict | None = None,
    limit: int = 8,
    candidate_pool: int = 60,
) -> list[Recommendation]:
    """Full pipeline: taste vector from the viewer's films → TMDB candidates → score → top `limit`.

    A free-text `prompt` (what the user is in the mood for) is embedded locally and used to both seed
    discovery and tilt scoring — the ranking still happens in Python, the model never decides.
    """
    tmdb = tmdb or TMDBService()

    # Build the search plan from the parsed intent (LLM) when present, else from the embedding alone.
    # The LLM only translates the request; this plan and everything below it is pure Python.
    prompt_text = (prompt or "").strip() or None
    plan = _build_search_plan(prompt_text, intent, tmdb) if prompt_text else None

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

    if plan:
        candidate_ids = discover_candidate_ids(
            tmdb, evidence, watched_ids, mood, candidate_pool,
            prompt_genres=plan["genres"], and_genres=plan["and_genres"],
            exclude_genres=plan["exclude_genres"], keyword_ids=plan["keyword_ids"],
            min_rating=plan["min_rating"],
        )
    else:
        candidate_ids = discover_candidate_ids(tmdb, evidence, watched_ids, mood, candidate_pool)
    svc = EnrichmentService(tmdb)
    candidate_films: list[Film] = []
    for tid in candidate_ids:
        film = svc.get_or_create_by_tmdb_id(db, tid)
        if film:
            candidate_films.append(film)

    # Drop films whose own description carries an excluded term (standup/concert/tragedy) — the
    # reliable removal of non-narrative/off-tone content that TMDB genre tags leave in.
    if plan and plan["exclude_terms"]:
        kept = [f for f in candidate_films if not _film_hits_terms(f, plan["exclude_terms"])]
        if len(kept) < len(candidate_films):
            logger.info("ranker: excluded %d films on terms", len(candidate_films) - len(kept))
        candidate_films = kept

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
    if plan:
        return rank_candidates(
            taste, vectors, watched_ids, evidence, limit, plan["vec"], plan["text"], plan["gwts"]
        )
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

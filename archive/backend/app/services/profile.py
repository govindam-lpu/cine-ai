from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.entities import Film, TasteProfile, User, WatchHistory
from app.services.tmdb import TMDBService


DARK_GENRES = {"Crime", "Horror", "Mystery", "Thriller", "War"}
LIGHT_GENRES = {"Adventure", "Animation", "Comedy", "Family", "Romance"}
FAST_GENRES = {"Action", "Adventure", "Horror", "Thriller"}
SLOW_GENRES = {"Documentary", "Drama", "History", "Romance"}
INTELLECTUAL_GENRES = {"Documentary", "History", "Mystery", "Science Fiction", "Sci-Fi"}
EMOTIONAL_GENRES = {"Drama", "Family", "Music", "Romance"}
EMOTION_GENRES = {
    "Melancholy": {"Drama", "History", "War"},
    "Awe": {"Adventure", "Fantasy", "Science Fiction", "Sci-Fi"},
    "Tension": {"Crime", "Horror", "Mystery", "Thriller"},
    "Warmth": {"Comedy", "Family", "Romance"},
}


class ProfileService:
    def __init__(self) -> None:
        self.tmdb = TMDBService()

    def build_profile(self, db: Session, user_id: str) -> dict | None:
        user = db.get(User, user_id)
        if not user:
            return None

        rows = (
            db.query(WatchHistory, Film)
            .join(Film, WatchHistory.film_id == Film.id)
            .filter(WatchHistory.user_id == user_id)
            .all()
        )
        if not rows:
            return {"not_ready": True, "reason": "No watch history has been imported yet"}

        films = [film for _, film in rows]
        histories = [history for history, _ in rows]
        rated = [(history.user_rating, film) for history, film in rows if history.user_rating is not None]
        overall_rating = sum(rating for rating, _ in rated) / len(rated) if rated else None

        top_genres = self._genre_stats(rows)
        preferred_eras = self._era_stats(rows)
        emotional_aftertastes = self._emotion_stats(rows)
        tone_profile = self._tone_profile(films)
        pretension_score = self._pretension_score(films)
        crew = self._crew_affinities(rows)
        invisible_preferences = self._invisible_preferences(rows, top_genres, preferred_eras, overall_rating)
        negative_signals = self._negative_signals(rows, overall_rating)

        summary = self._summary(
            films_analyzed=len(rows),
            top_genres=top_genres,
            preferred_eras=preferred_eras,
            tone_profile=tone_profile,
            overall_rating=overall_rating,
            rewatch_count=sum(1 for history in histories if history.is_rewatch),
        )
        fingerprint = self._fingerprint(top_genres, preferred_eras, tone_profile)

        self._save_summary(db, user_id, summary)

        return {
            "summary": summary,
            "taste_summary": summary,
            "fingerprint": fingerprint,
            "taste_fingerprint": fingerprint,
            "top_genres": top_genres,
            "preferred_eras": preferred_eras,
            "tone_profile": tone_profile,
            "narrative_preference": self._narrative_preference(top_genres),
            "pacing_preference": "fast" if tone_profile["slow_fast"] > 0.18 else "slow_burn" if tone_profile["slow_fast"] < -0.18 else "mixed",
            "ending_preference": "unresolved" if any(item["genre"] in {"Mystery", "Thriller", "Drama"} for item in top_genres[:3]) else "resolved",
            "top_directors": crew["directors"],
            "top_cinematographers": crew["cinematographers"],
            "top_composers": crew["composers"],
            "crew_affinities": crew["combined"],
            "invisible_preferences": invisible_preferences,
            "negative_signals": negative_signals,
            "emotional_aftertastes": emotional_aftertastes,
            "pretension_score": pretension_score,
            "blind_spots": self._blind_spots(top_genres, preferred_eras),
            "timeline": self._timeline(user, len(rows), len(rated)),
            "films_analyzed": len(rows),
            "rated_films_analyzed": len(rated),
            "profile_version": 1,
            "backendReady": True,
            "updated_at": datetime.utcnow().isoformat(),
            "data_sources": ["letterboxd", "tmdb"],
        }

    @staticmethod
    def _genre_stats(rows) -> list[dict]:
        counts: Counter[str] = Counter()
        rating_sums: defaultdict[str, float] = defaultdict(float)
        rating_counts: Counter[str] = Counter()
        total_films = len(rows)

        for history, film in rows:
            for genre in film.genres or []:
                counts[genre] += 1
                if history.user_rating is not None:
                    rating_sums[genre] += history.user_rating
                    rating_counts[genre] += 1

        stats = []
        for genre, count in counts.most_common(8):
            avg_rating = rating_sums[genre] / rating_counts[genre] if rating_counts[genre] else None
            stats.append(
                {
                    "genre": genre,
                    "value": round((count / total_films) * 100),
                    "count": count,
                    "avg_rating": round(avg_rating, 2) if avg_rating is not None else None,
                }
            )
        return stats

    @staticmethod
    def _era_stats(rows) -> list[dict]:
        counts: Counter[str] = Counter()
        rating_sums: defaultdict[str, float] = defaultdict(float)
        rating_counts: Counter[str] = Counter()
        total_films = len(rows)

        for history, film in rows:
            if not film.release_year:
                continue
            decade = f"{(film.release_year // 10) * 10}s"
            counts[decade] += 1
            if history.user_rating is not None:
                rating_sums[decade] += history.user_rating
                rating_counts[decade] += 1

        return [
            {
                "genre": decade,
                "decade": decade,
                "value": round((count / total_films) * 100),
                "count": count,
                "avg_rating": round(rating_sums[decade] / rating_counts[decade], 2) if rating_counts[decade] else None,
            }
            for decade, count in counts.most_common(8)
        ]

    @staticmethod
    def _tone_profile(films: list[Film]) -> dict:
        def axis(positive: set[str], negative: set[str], vote_weight: bool = False) -> float:
            score = 0.0
            seen = 0
            for film in films:
                genres = set(film.genres or [])
                if genres & positive:
                    score += 1
                    seen += 1
                if genres & negative:
                    score -= 1
                    seen += 1
                if vote_weight and film.tmdb_vote_count:
                    score += 0.35 if film.tmdb_vote_count >= 3000 else -0.25
                    seen += 1
            if not seen:
                return 0.0
            return max(-1.0, min(1.0, round(score / seen, 2)))

        return {
            "dark_light": axis(LIGHT_GENRES, DARK_GENRES),
            "slow_fast": axis(FAST_GENRES, SLOW_GENRES),
            "emotional_intellectual": axis(INTELLECTUAL_GENRES, EMOTIONAL_GENRES),
            "arthouse_mainstream": axis(set(), set(), vote_weight=True),
        }

    @staticmethod
    def _emotion_stats(rows) -> list[dict]:
        scores: defaultdict[str, float] = defaultdict(float)
        total = 0.0
        for history, film in rows:
            genres = set(film.genres or [])
            weight = history.user_rating if history.user_rating is not None else 3.0
            for emotion, mapped_genres in EMOTION_GENRES.items():
                if genres & mapped_genres:
                    scores[emotion] += weight
                    total += weight
        if not scores:
            return []
        max_score = max(scores.values())
        return [
            {"genre": emotion, "emotion": emotion.lower(), "value": round((score / max_score) * 100), "correlation_score": round(score / total, 2)}
            for emotion, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
        ]

    @staticmethod
    def _pretension_score(films: list[Film]) -> float:
        if not films:
            return 0.0
        score = 0.0
        for film in films:
            if film.original_language and film.original_language != "en":
                score += 0.22
            if film.tmdb_vote_count is not None and film.tmdb_vote_count < 800:
                score += 0.28
            if film.runtime_minutes and film.runtime_minutes >= 135:
                score += 0.16
            if film.genres and {"Documentary", "History"} & set(film.genres):
                score += 0.14
        return round(max(0.0, min(1.0, score / len(films))), 2)

    def _crew_affinities(self, rows) -> dict:
        directors: Counter[str] = Counter()
        cinematographers: Counter[str] = Counter()
        composers: Counter[str] = Counter()

        ranked_rows = sorted(rows, key=lambda row: row[0].user_rating if row[0].user_rating is not None else 0, reverse=True)
        for history, film in ranked_rows[:24]:
            if not film.tmdb_id:
                continue
            try:
                credits = self.tmdb.movie_credits(film.tmdb_id)
            except Exception:  # noqa: BLE001
                continue
            weight = max(1, int(round((history.user_rating or 3.0) * 2)))
            for person in credits.get("crew", []):
                name = person.get("name")
                job = person.get("job")
                department = person.get("department")
                if not name:
                    continue
                if job == "Director":
                    directors[name] += weight
                elif job in {"Director of Photography", "Cinematography"}:
                    cinematographers[name] += weight
                elif job in {"Original Music Composer", "Music"} or department == "Sound":
                    composers[name] += weight

        combined = []
        for bucket in (directors, cinematographers, composers):
            combined.extend([name for name, _ in bucket.most_common(3)])

        return {
            "directors": [name for name, _ in directors.most_common(5)],
            "cinematographers": [name for name, _ in cinematographers.most_common(5)],
            "composers": [name for name, _ in composers.most_common(5)],
            "combined": combined[:8],
        }

    @staticmethod
    def _invisible_preferences(rows, top_genres: list[dict], preferred_eras: list[dict], overall_rating: float | None) -> list[str]:
        preferences = []
        long_ratings = [history.user_rating for history, film in rows if history.user_rating is not None and film.runtime_minutes and film.runtime_minutes >= 130]
        short_ratings = [history.user_rating for history, film in rows if history.user_rating is not None and film.runtime_minutes and film.runtime_minutes < 100]
        if long_ratings and short_ratings and sum(long_ratings) / len(long_ratings) > sum(short_ratings) / len(short_ratings) + 0.25:
            preferences.append("Longer films are rating above shorter films in your imported history.")
        if top_genres:
            top = top_genres[0]
            preferences.append(f"{top['genre']} is the strongest genre signal, appearing in {top['count']} imported films.")
        if preferred_eras:
            era = preferred_eras[0]
            preferences.append(f"Your most represented era is the {era['decade']}, with {era['count']} imported films.")
        non_english = [film for _, film in rows if film.original_language and film.original_language != "en"]
        if non_english:
            preferences.append(f"Non-English films make up {round((len(non_english) / len(rows)) * 100)}% of the imported profile.")
        if overall_rating is not None:
            preferences.append(f"Your rated-film average is {overall_rating:.2f} out of 5 across imported Letterboxd ratings.")
        return preferences[:5]

    @staticmethod
    def _negative_signals(rows, overall_rating: float | None) -> list[str]:
        if overall_rating is None:
            return ["No strong negative rating signal is available yet because too few imported films have ratings."]

        genre_ratings: defaultdict[str, list[float]] = defaultdict(list)
        for history, film in rows:
            if history.user_rating is None:
                continue
            for genre in film.genres or []:
                genre_ratings[genre].append(history.user_rating)

        signals = []
        for genre, ratings in genre_ratings.items():
            if len(ratings) >= 2:
                avg = sum(ratings) / len(ratings)
                if avg <= overall_rating - 0.35:
                    signals.append(f"{genre} is underperforming your overall average at {avg:.2f} out of 5.")
        return signals[:4] or ["No consistent negative genre signal has emerged from the imported ratings yet."]

    @staticmethod
    def _blind_spots(top_genres: list[dict], preferred_eras: list[dict]) -> dict:
        seen_genres = {item["genre"] for item in top_genres}
        seen_eras = {item["decade"] for item in preferred_eras}
        candidate_genres = ["Western", "Music", "Documentary", "Animation", "History"]
        candidate_eras = ["1950s", "1960s", "1970s", "1980s"]
        return {
            "genres": [genre for genre in candidate_genres if genre not in seen_genres][:3],
            "decades": [era for era in candidate_eras if era not in seen_eras][:3],
            "countries": [],
        }

    @staticmethod
    def _summary(films_analyzed: int, top_genres: list[dict], preferred_eras: list[dict], tone_profile: dict, overall_rating: float | None, rewatch_count: int) -> str:
        genre = top_genres[0]["genre"] if top_genres else "mixed genres"
        era = preferred_eras[0]["decade"] if preferred_eras else "multiple eras"
        tone = "darker" if tone_profile["dark_light"] < -0.15 else "lighter" if tone_profile["dark_light"] > 0.15 else "tonally balanced"
        rating = f" with a {overall_rating:.2f}/5 average rating" if overall_rating is not None else ""
        return f"Analyzed {films_analyzed} imported films{rating}. The strongest signals are {genre}, the {era}, and a {tone} tilt, with {rewatch_count} rewatch markers shaping the profile."

    @staticmethod
    def _fingerprint(top_genres: list[dict], preferred_eras: list[dict], tone_profile: dict) -> str:
        genre_bits = " / ".join(item["genre"] for item in top_genres[:3]) or "mixed genre"
        era = preferred_eras[0]["decade"] if preferred_eras else "cross-era"
        pace = "kinetic" if tone_profile["slow_fast"] > 0.15 else "patient" if tone_profile["slow_fast"] < -0.15 else "varied pace"
        return f"{genre_bits} | {era} | {pace}"

    @staticmethod
    def _narrative_preference(top_genres: list[dict]) -> str:
        genres = {item["genre"] for item in top_genres[:4]}
        if genres & {"Mystery", "Science Fiction", "Sci-Fi", "Thriller"}:
            return "concept"
        if genres & {"Drama", "Romance", "Family"}:
            return "character"
        return "mixed"

    @staticmethod
    def _timeline(user: User, films_analyzed: int, rated_count: int) -> list[dict]:
        return [
            {"label": "Connect", "description": "Letterboxd account linked through a public username."},
            {"label": "Import", "description": f"{films_analyzed} films are currently stored in local watch history."},
            {"label": "Ratings", "description": f"{rated_count} imported entries include a Letterboxd rating."},
            {"label": "Refresh", "description": f"Last sync: {user.last_synced_at.isoformat() if user.last_synced_at else 'not yet synced'}."},
        ]

    @staticmethod
    def _save_summary(db: Session, user_id: str, summary: str) -> None:
        profile = db.query(TasteProfile).filter_by(user_id=user_id).first()
        if profile:
            profile.taste_summary = summary
            profile.updated_at = datetime.utcnow()
        else:
            db.add(TasteProfile(user_id=user_id, taste_summary=summary))
        db.commit()

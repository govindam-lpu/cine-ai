from collections import Counter, defaultdict
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.entities import Film, User, WatchHistory
from app.services.tmdb import TMDBService


GENRE_TO_TMDB_ID = {
    "Action": 28,
    "Adventure": 12,
    "Animation": 16,
    "Comedy": 35,
    "Crime": 80,
    "Documentary": 99,
    "Drama": 18,
    "Family": 10751,
    "Fantasy": 14,
    "History": 36,
    "Horror": 27,
    "Music": 10402,
    "Mystery": 9648,
    "Romance": 10749,
    "Science Fiction": 878,
    "Sci-Fi": 878,
    "Thriller": 53,
    "War": 10752,
    "Western": 37,
}
TMDB_ID_TO_GENRE = {value: key for key, value in GENRE_TO_TMDB_ID.items() if key != "Sci-Fi"}


class RecommendationService:
    def __init__(self) -> None:
        self.tmdb = TMDBService()

    def recommendations_for_user(self, db: Session, user_id: str, limit: int = 8, mood: str | None = None) -> dict | None:
        user = db.get(User, user_id)
        if not user:
            return None

        rows = (
            db.query(WatchHistory, Film)
            .join(Film, WatchHistory.film_id == Film.id)
            .filter(WatchHistory.user_id == user_id)
            .all()
        )
        if len(rows) < 10:
            return {"not_ready": True, "reason": "At least 10 imported films are needed before recommendations can be ranked"}

        watched_tmdb_ids = {film.tmdb_id for _, film in rows if film.tmdb_id}
        genre_stats = self._genre_stats(rows)
        top_genres = [item["genre"] for item in genre_stats[:4]]
        candidates = self._discover_candidates(top_genres, watched_tmdb_ids, limit=max(limit + 4, 12), mood=mood)

        recommendations = []
        for movie in candidates:
            item = self._recommendation_item(movie, genre_stats, rows)
            if item:
                recommendations.append(item)
            if len(recommendations) >= limit:
                break

        wild_card = self._wild_card(genre_stats, watched_tmdb_ids)
        anti = self._anti_recommendation(rows, watched_tmdb_ids)

        return {
            "recommendations": recommendations,
            "wild_card": wild_card,
            "anti_recommendations": [anti] if anti else [],
            "generated_at": datetime.utcnow().isoformat(),
            "basis": {
                "films_analyzed": len(rows),
                "top_genres": genre_stats[:5],
                "mood": mood,
            },
        }

    @staticmethod
    def _genre_stats(rows) -> list[dict]:
        counts: Counter[str] = Counter()
        rating_sums: defaultdict[str, float] = defaultdict(float)
        rating_counts: Counter[str] = Counter()
        for history, film in rows:
            for genre in film.genres or []:
                counts[genre] += 1
                if history.user_rating is not None:
                    rating_sums[genre] += history.user_rating
                    rating_counts[genre] += 1
        stats = []
        for genre, count in counts.most_common():
            avg = rating_sums[genre] / rating_counts[genre] if rating_counts[genre] else None
            stats.append({"genre": genre, "count": count, "avg_rating": avg})
        return stats

    def _discover_candidates(self, genres: list[str], watched_tmdb_ids: set[int], limit: int, mood: str | None) -> list[dict]:
        candidates: list[dict] = []
        seen = set(watched_tmdb_ids)
        genre_ids = [GENRE_TO_TMDB_ID[genre] for genre in genres if genre in GENRE_TO_TMDB_ID]
        if mood:
            genre_ids = self._apply_mood(genre_ids, mood)
        if not genre_ids:
            genre_ids = [18]

        for genre_id in genre_ids[:4]:
            try:
                payload = self.tmdb.discover_movies(
                    {
                        "with_genres": str(genre_id),
                        "sort_by": "vote_average.desc",
                        "vote_count.gte": 250,
                        "include_adult": "false",
                        "primary_release_date.lte": date.today().isoformat(),
                        "page": 1,
                    }
                )
            except Exception:  # noqa: BLE001
                continue
            for movie in payload.get("results", []):
                tmdb_id = movie.get("id")
                if not tmdb_id or tmdb_id in seen:
                    continue
                seen.add(tmdb_id)
                candidates.append(movie)
                if len(candidates) >= limit:
                    return candidates
        return candidates

    @staticmethod
    def _apply_mood(genre_ids: list[int], mood: str) -> list[int]:
        lowered = mood.lower()
        mood_ids = []
        if "cry" in lowered:
            mood_ids.extend([18, 10749])
        if "comfort" in lowered or "low" in lowered:
            mood_ids.extend([35, 10751, 16])
        if "disturb" in lowered:
            mood_ids.extend([27, 53])
        if "date" in lowered:
            mood_ids.extend([10749, 35])
        if "think" in lowered:
            mood_ids.extend([878, 9648, 99])
        return list(dict.fromkeys(mood_ids + genre_ids))

    def _recommendation_item(self, movie: dict, genre_stats: list[dict], rows) -> dict | None:
        details = self._details(movie)
        tmdb_id = details.get("id") or movie.get("id")
        if not tmdb_id:
            return None

        genres = [genre.get("name") for genre in details.get("genres", []) if genre.get("name")]
        if not genres and movie.get("genre_ids"):
            genres = [TMDB_ID_TO_GENRE.get(genre_id, str(genre_id)) for genre_id in movie.get("genre_ids", [])]

        matching_stat = next((stat for stat in genre_stats if stat["genre"] in genres), genre_stats[0] if genre_stats else None)
        predicted = self._predicted_rating(details, matching_stat)
        confidence = "high" if predicted >= 4.15 else "medium"

        return {
            "film": {
                "tmdb_id": tmdb_id,
                "media_type": "film",
                "title": details.get("title") or movie.get("title"),
                "release_year": self._year(details.get("release_date") or movie.get("release_date")),
                "runtime_minutes": details.get("runtime") or 0,
                "genres": genres,
                "directors": self._directors(tmdb_id),
                "poster_path": details.get("poster_path") or movie.get("poster_path"),
                "tmdb_rating": details.get("vote_average") or movie.get("vote_average"),
                "overview": details.get("overview") or movie.get("overview"),
            },
            "reason": self._reason(details, genres, matching_stat, rows),
            "confidence": confidence,
            "tags": self._tags(details, genres, matching_stat),
            "streaming": [],
            "predicted_rating": predicted,
            "is_wild_card": False,
        }

    def _wild_card(self, genre_stats: list[dict], watched_tmdb_ids: set[int]) -> dict | None:
        seen_genres = {stat["genre"] for stat in genre_stats[:6]}
        for genre, genre_id in GENRE_TO_TMDB_ID.items():
            if genre in seen_genres:
                continue
            candidates = self._discover_candidates([genre], watched_tmdb_ids, limit=4, mood=None)
            if not candidates:
                continue
            item = self._recommendation_item(candidates[0], genre_stats, [])
            if item:
                item["confidence"] = "wild"
                item["is_wild_card"] = True
                item["reason"] = f"{genre} is not one of your dominant imported signals, making this a deliberate expansion pick rather than a comfort-zone match."
                return item
        return None

    def _anti_recommendation(self, rows, watched_tmdb_ids: set[int]) -> dict | None:
        genre_ratings: defaultdict[str, list[float]] = defaultdict(list)
        for history, film in rows:
            if history.user_rating is None:
                continue
            for genre in film.genres or []:
                genre_ratings[genre].append(history.user_rating)
        if not genre_ratings:
            return None
        low_genres = sorted(
            [(genre, sum(ratings) / len(ratings), len(ratings)) for genre, ratings in genre_ratings.items() if len(ratings) >= 2],
            key=lambda item: item[1],
        )
        if not low_genres:
            return None
        genre, avg, _ = low_genres[0]
        candidates = self._discover_candidates([genre], watched_tmdb_ids, limit=3, mood=None)
        if not candidates:
            return None
        item = self._recommendation_item(candidates[0], [{"genre": genre, "count": 0, "avg_rating": avg}], rows)
        if not item:
            return None
        return {
            "film": item["film"],
            "reason": f"{genre} is currently your weakest rated genre signal at {avg:.2f}/5, so this is a likely poor fit despite external popularity.",
            "confidence": "medium",
        }

    def _details(self, movie: dict) -> dict:
        try:
            return self.tmdb.movie_details(movie["id"])
        except Exception:  # noqa: BLE001
            return movie

    def _directors(self, tmdb_id: int) -> list[str]:
        try:
            credits = self.tmdb.movie_credits(tmdb_id)
        except Exception:  # noqa: BLE001
            return []
        return [person["name"] for person in credits.get("crew", []) if person.get("job") == "Director" and person.get("name")][:3]

    @staticmethod
    def _predicted_rating(details: dict, matching_stat: dict | None) -> float:
        base = matching_stat.get("avg_rating") if matching_stat and matching_stat.get("avg_rating") is not None else 3.4
        tmdb = details.get("vote_average") or 7.0
        score = (base * 0.72) + ((tmdb / 2) * 0.28)
        return round(max(1.0, min(5.0, score)), 1)

    @staticmethod
    def _reason(details: dict, genres: list[str], matching_stat: dict | None, rows) -> str:
        title = details.get("title") or "This pick"
        if matching_stat:
            genre = matching_stat["genre"]
            avg = matching_stat.get("avg_rating")
            rating_line = f" with a {avg:.2f}/5 average" if avg is not None else ""
            return f"{title} matches your {genre} signal across {matching_stat['count']} imported films{rating_line}, while staying outside titles already in your Letterboxd history."
        return f"{title} is ranked from TMDB metadata after excluding your imported Letterboxd history."

    @staticmethod
    def _tags(details: dict, genres: list[str], matching_stat: dict | None) -> list[str]:
        tags = genres[:3]
        if details.get("runtime") and details["runtime"] >= 130:
            tags.append("long-form")
        if matching_stat and matching_stat.get("avg_rating") and matching_stat["avg_rating"] >= 4:
            tags.append("high-signal genre")
        return tags[:4]

    @staticmethod
    def _year(value: str | None) -> int:
        if value and len(value) >= 4 and value[:4].isdigit():
            return int(value[:4])
        return 0

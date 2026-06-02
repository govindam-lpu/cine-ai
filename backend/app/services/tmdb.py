from difflib import SequenceMatcher

import requests

from app.core.config import settings


class TMDBService:
    def __init__(self) -> None:
        self.api_key = settings.tmdb_api_key
        self.bearer_token = settings.tmdb_bearer_token
        self.base_url = settings.tmdb_base_url

    def _get(self, path: str, params: dict) -> dict:
        if not self.api_key and not self.bearer_token:
            return {}
        headers = {"accept": "application/json"}
        payload = dict(params)
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        elif self.api_key:
            payload["api_key"] = self.api_key
        response = requests.get(f"{self.base_url}{path}", params=payload, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()

    def search_movie_match(self, title: str, year: int | None) -> dict | None:
        if not title:
            return None
        primary = self._get("/search/movie", {"query": title, "year": year} if year else {"query": title})
        results = primary.get("results", [])
        best = self._pick_best(results, title, year)
        if best:
            return best
        if year:
            fallback = self._get("/search/movie", {"query": title})
            return self._pick_best(fallback.get("results", []), title, None)
        return None

    def movie_details(self, tmdb_id: int) -> dict:
        return self._get(f"/movie/{tmdb_id}", {})

    def movie_credits(self, tmdb_id: int) -> dict:
        return self._get(f"/movie/{tmdb_id}/credits", {})

    def discover_movies(self, params: dict) -> dict:
        return self._get("/discover/movie", params)

    @staticmethod
    def _pick_best(results: list[dict], title: str, year: int | None) -> dict | None:
        for result in results[:5]:
            candidate = result.get("title") or ""
            ratio = SequenceMatcher(None, candidate.lower(), title.lower()).ratio()
            release = result.get("release_date", "")
            release_year = int(release[:4]) if len(release) >= 4 and release[:4].isdigit() else None
            if ratio > 0.9 and (year is None or year == release_year):
                return result
        return results[0] if results else None

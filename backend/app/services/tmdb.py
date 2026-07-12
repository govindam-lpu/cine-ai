"""TMDB client — live search / details / credits / discover with fuzzy title matching.

Ported essentially as-is from the archive (good code with real edge handling), extended with
`append_to_response` so one details call can return credits + keywords together — cutting
enrichment from three requests per film to two. Absent API keys degrade gracefully: `_get`
returns `{}` rather than raising, so the app boots and runs without them.

Requests go through a pooled `requests.Session` with HTTP keep-alive, so enrichment's many
calls reuse connections instead of paying a fresh TLS handshake each time (~300ms saved per
call on a distant network). The session is shared across enrichment's worker threads — safe,
because urllib3's connection pool is thread-safe for GETs — and retries 429/5xx with backoff.
"""

from difflib import SequenceMatcher

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import settings


def _build_session(bearer_token: str) -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,                       # 0.5s → 1s → 2s between attempts
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,          # honor TMDB's Retry-After on 429
        raise_on_status=False,
    )
    # Pool sized to comfortably cover the enrichment concurrency.
    pool = max(32, settings.tmdb_concurrency * 2)
    adapter = HTTPAdapter(max_retries=retry, pool_connections=pool, pool_maxsize=pool)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers["accept"] = "application/json"
    if bearer_token:
        session.headers["Authorization"] = f"Bearer {bearer_token}"
    return session


_KEYWORD_ID_CACHE: dict[str, int | None] = {}


class TMDBService:
    def __init__(self) -> None:
        self.api_key = settings.tmdb_api_key
        self.bearer_token = settings.tmdb_bearer_token
        self.base_url = settings.tmdb_base_url
        self.session = _build_session(self.bearer_token)

    @property
    def configured(self) -> bool:
        if settings.e2e_mode:
            return False  # e2e runs offline → discovery falls back to the seeded film cache
        return bool(self.api_key or self.bearer_token)

    def _get(self, path: str, params: dict) -> dict:
        if not self.configured:
            return {}
        payload = dict(params)
        if not self.bearer_token and self.api_key:
            payload["api_key"] = self.api_key      # bearer (if set) rides on the session header
        response = self.session.get(f"{self.base_url}{path}", params=payload, timeout=20)
        response.raise_for_status()
        return response.json()

    def search_movie_match(self, title: str, year: int | None) -> dict | None:
        if not title:
            return None
        primary = self._get(
            "/search/movie", {"query": title, "year": year} if year else {"query": title}
        )
        results = primary.get("results", [])
        best = self._pick_best(results, title, year)
        if best:
            return best
        if year:
            fallback = self._get("/search/movie", {"query": title})
            return self._pick_best(fallback.get("results", []), title, None)
        return None

    def movie_details(self, tmdb_id: int, append: str | None = None) -> dict:
        params = {"append_to_response": append} if append else {}
        return self._get(f"/movie/{tmdb_id}", params)

    def movie_credits(self, tmdb_id: int) -> dict:
        return self._get(f"/movie/{tmdb_id}/credits", {})

    def discover_movies(self, params: dict) -> dict:
        return self._get("/discover/movie", params)

    def search_keyword_ids(self, phrases: list[str]) -> list[int]:
        """Resolve theme phrases (e.g. 'feel-good') to TMDB keyword ids for discover's with_keywords.
        Cached process-wide — keyword ids are stable. Unresolvable phrases are skipped, not fatal."""
        ids: list[int] = []
        for phrase in phrases:
            key = (phrase or "").strip().lower()
            if not key:
                continue
            if key not in _KEYWORD_ID_CACHE:
                try:
                    results = self._get("/search/keyword", {"query": key}).get("results", [])
                    _KEYWORD_ID_CACHE[key] = results[0]["id"] if results else None
                except Exception:  # noqa: BLE001
                    _KEYWORD_ID_CACHE[key] = None
            kid = _KEYWORD_ID_CACHE[key]
            if kid is not None:
                ids.append(kid)
        return ids

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

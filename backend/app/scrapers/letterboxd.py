import random
import time
from dataclasses import dataclass
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from app.utils.ratings import parse_letterboxd_rating


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)


class ScrapeError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class FilmEntry:
    title: str
    year: int | None
    letterboxd_slug: str
    user_rating: float | None
    watched_at: datetime | None = None
    is_rewatch: bool = False


@dataclass
class ProfileInfo:
    username: str
    display_name: str | None
    avatar_url: str | None
    is_private: bool


class LetterboxdScraper:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def preflight(self, username: str) -> ProfileInfo:
        url = f"https://letterboxd.com/{username}/"
        response = self.session.get(url, timeout=20)
        if response.status_code == 404:
            raise ScrapeError("PROFILE_NOT_FOUND", "Letterboxd profile not found")
        if response.status_code >= 400:
            raise ScrapeError("SCRAPE_FAILED", "Could not reach Letterboxd")

        soup = BeautifulSoup(response.text, "html.parser")
        private_copy = soup.get_text(" ", strip=True).lower()
        if "this profile is private" in private_copy:
            raise ScrapeError("PROFILE_PRIVATE", "Letterboxd profile is private")

        display_name = None
        heading = soup.select_one("h1.person-display-name") or soup.select_one("h1")
        if heading:
            display_name = heading.get_text(strip=True)

        avatar = soup.select_one("img.avatar")
        avatar_url = avatar.get("src") if avatar else None

        return ProfileInfo(username=username, display_name=display_name, avatar_url=avatar_url, is_private=False)

    def scrape_films(self, username: str, mode: str = "full") -> list[FilmEntry]:
        max_pages = 3 if mode == "incremental" else 100
        films: list[FilmEntry] = []

        for page in range(1, max_pages + 1):
            url = f"https://letterboxd.com/{username}/films/page/{page}/" if page > 1 else f"https://letterboxd.com/{username}/films/"
            response = self._fetch_with_backoff(url)
            if response.status_code == 404:
                break
            soup = BeautifulSoup(response.text, "html.parser")
            posters = soup.select("ul.poster-list li.poster-container div[data-film-slug]")
            if not posters:
                break

            for div in posters:
                slug = div.get("data-film-slug")
                title = div.get("data-film-name")
                year = int(div.get("data-film-year")) if div.get("data-film-year", "").isdigit() else None
                if not slug or not title:
                    continue
                rating_el = div.select_one("span.rating")
                rating = parse_letterboxd_rating(rating_el.get_text(strip=True) if rating_el else None)
                rewatch = bool(div.select_one("span.rewatch"))
                films.append(FilmEntry(title=title, year=year, letterboxd_slug=f"/film/{slug}/", user_rating=rating, is_rewatch=rewatch))

            time.sleep(random.uniform(1.5, 3.5))

        return films

    def _fetch_with_backoff(self, url: str) -> requests.Response:
        for attempt in range(4):
            response = self.session.get(url, timeout=30)
            text = response.text.lower()
            if response.status_code != 429 and "cloudflare" not in text:
                return response
            if attempt == 3:
                raise ScrapeError("SCRAPE_BLOCKED", "Blocked by Letterboxd/Cloudflare")
            time.sleep(60)
        raise ScrapeError("SCRAPE_FAILED", "Request failed")

"""Letterboxd scraper — LOCAL DEV ONLY.

Ported from the archive. Cloudflare 403s datacenter IPs (verified — the whole reason the public
path is CSV upload, not scraping), so this only works from a residential IP. It stays in the tree
as a local-dev convenience and a switch to flip back on if a Letterboxd API is ever granted.
Never wire this into the deployed ingestion path.

Carries the good edge handling: block/backoff detection, an RSS fallback that ships TMDB IDs,
and private/404 profile detection.
"""

import random
import re
import time
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from xml.etree import ElementTree

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
    tmdb_id: int | None = None
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
        try:
            response = self.session.get(url, timeout=20)
        except requests.RequestException as exc:
            raise ScrapeError("SCRAPE_FAILED", "Could not reach Letterboxd") from exc
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

        return ProfileInfo(
            username=username, display_name=display_name, avatar_url=avatar_url, is_private=False
        )

    def scrape_films(self, username: str, mode: str = "full") -> list[FilmEntry]:
        max_pages = 3 if mode == "incremental" else 100
        films: list[FilmEntry] = []

        try:
            for page in range(1, max_pages + 1):
                url = (
                    f"https://letterboxd.com/{username}/films/page/{page}/"
                    if page > 1
                    else f"https://letterboxd.com/{username}/films/"
                )
                response = self._fetch_with_backoff(url)
                if response.status_code == 404:
                    break
                soup = BeautifulSoup(response.text, "html.parser")
                posters = self._find_poster_nodes(soup)
                if not posters:
                    break

                for div in posters:
                    entry = self._entry_from_poster_node(div)
                    if entry:
                        films.append(entry)

                time.sleep(random.uniform(1.5, 3.5))
        except ScrapeError as exc:
            if exc.code != "SCRAPE_BLOCKED":
                raise
            films = self._scrape_rss_fallback(username)

        if not films:
            films = self._scrape_rss_fallback(username)

        if not films:
            raise ScrapeError("NO_FILMS_FOUND", "No public Letterboxd films were found")

        return films

    def _fetch_with_backoff(self, url: str) -> requests.Response:
        for attempt in range(4):
            try:
                response = self.session.get(url, timeout=30)
            except requests.RequestException as exc:
                if attempt == 3:
                    raise ScrapeError("SCRAPE_FAILED", "Letterboxd request failed") from exc
                time.sleep(5)
                continue
            text = response.text.lower()
            hard_blocked = (
                response.status_code == 403
                or "just a moment" in text
                or "enable javascript and cookies" in text
            )
            rate_limited = response.status_code == 429 or "cloudflare" in text
            if hard_blocked:
                raise ScrapeError("SCRAPE_BLOCKED", "Blocked by Letterboxd/Cloudflare")
            if not rate_limited:
                return response
            if attempt == 3:
                raise ScrapeError("SCRAPE_BLOCKED", "Blocked by Letterboxd/Cloudflare")
            time.sleep(60)
        raise ScrapeError("SCRAPE_FAILED", "Request failed")

    @staticmethod
    def _find_poster_nodes(soup: BeautifulSoup):
        selectors = [
            "ul.poster-list li.poster-container div[data-film-slug]",
            "li.poster-container div[data-film-slug]",
            "li.posteritem div[data-film-slug]",
            "div.film-poster[data-film-slug]",
            "div[data-film-slug][data-film-name]",
        ]
        for selector in selectors:
            matches = soup.select(selector)
            if matches:
                return matches
        return []

    @staticmethod
    def _entry_from_poster_node(div) -> FilmEntry | None:
        slug = div.get("data-film-slug")
        title = div.get("data-film-name") or div.get("data-item-name")
        year_value = div.get("data-film-year") or div.get("data-item-year")
        year = int(year_value) if year_value and year_value.isdigit() else None
        if not slug or not title:
            return None
        rating_el = div.select_one("span.rating")
        rating = parse_letterboxd_rating(rating_el.get_text(strip=True) if rating_el else None)
        rewatch = bool(div.select_one("span.rewatch"))
        return FilmEntry(
            title=title,
            year=year,
            letterboxd_slug=f"/film/{slug}/",
            user_rating=rating,
            is_rewatch=rewatch,
        )

    def _scrape_rss_fallback(self, username: str) -> list[FilmEntry]:
        response = self._fetch_rss(username)
        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError as exc:
            raise ScrapeError("SCRAPE_FAILED", "Could not parse Letterboxd RSS feed") from exc

        entries: dict[str, FilmEntry] = {}
        for item in root.findall("./channel/item"):
            title = self._xml_text(item, "{https://letterboxd.com}filmTitle")
            year_raw = self._xml_text(item, "{https://letterboxd.com}filmYear")
            rating_raw = self._xml_text(item, "{https://letterboxd.com}memberRating")
            watched_raw = self._xml_text(item, "{https://letterboxd.com}watchedDate")
            rewatch_raw = self._xml_text(item, "{https://letterboxd.com}rewatch")
            tmdb_raw = self._xml_text(item, "{https://themoviedb.org}movieId")
            link = self._xml_text(item, "link")

            slug = self._slug_from_link(link)
            if not title or not slug:
                continue

            year = int(year_raw) if year_raw and year_raw.isdigit() else None
            tmdb_id = int(tmdb_raw) if tmdb_raw and tmdb_raw.isdigit() else None
            watched_at = self._parse_rss_datetime(watched_raw) or self._parse_rss_datetime(
                self._xml_text(item, "pubDate")
            )
            key = str(tmdb_id) if tmdb_id else slug
            existing = entries.get(key)
            if existing:
                existing.is_rewatch = existing.is_rewatch or rewatch_raw == "Yes"
                if existing.user_rating is None and rating_raw:
                    existing.user_rating = float(rating_raw)
                if not existing.watched_at and watched_at:
                    existing.watched_at = watched_at
                continue

            entries[key] = FilmEntry(
                title=title,
                year=year,
                letterboxd_slug=f"/film/{slug}/",
                user_rating=float(rating_raw) if rating_raw else None,
                tmdb_id=tmdb_id,
                watched_at=watched_at,
                is_rewatch=rewatch_raw == "Yes",
            )

        return list(entries.values())

    def _fetch_rss(self, username: str) -> requests.Response:
        url = f"https://letterboxd.com/{username}/rss/"
        try:
            response = self.session.get(url, timeout=30)
        except requests.RequestException as exc:
            raise ScrapeError("SCRAPE_FAILED", "Could not reach Letterboxd RSS feed") from exc
        if response.status_code == 404:
            raise ScrapeError("PROFILE_NOT_FOUND", "Letterboxd profile not found")
        if response.status_code >= 400:
            raise ScrapeError("SCRAPE_FAILED", "Could not fetch Letterboxd RSS feed")
        return response

    @staticmethod
    def _xml_text(item: ElementTree.Element, tag: str) -> str | None:
        node = item.find(tag)
        if node is None or node.text is None:
            return None
        return node.text.strip()

    @staticmethod
    def _slug_from_link(link: str | None) -> str | None:
        if not link:
            return None
        match = re.search(r"/film/([^/]+)/?", link)
        return match.group(1) if match else None

    @staticmethod
    def _parse_rss_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                return datetime.fromisoformat(value)
            return parsedate_to_datetime(value).replace(tzinfo=None)
        except (TypeError, ValueError):
            return None

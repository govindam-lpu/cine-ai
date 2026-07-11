"""Letterboxd export parser — the public ingestion entry point.

Pure Python, no network. Takes the export (a ZIP of CSVs, or a single CSV) and produces a
de-duplicated list of films with rating / watched-date / rewatch. Enrichment (TMDB) happens
later, in enrich.py — the CSV carries no TMDB ID, so titles route through the matching client.

Defensive per Letterboxd's own rules: comma-delimited with quoted strings, UTF-8 (often with a
BOM), ratings as decimals 0.5–5.0 (NOT the ★ glyphs the scraper sees), dates as YYYY-MM-DD.
The "Letterboxd URI" yields a stable `/film/<slug>/` for both the film-page form (ratings/
watched) and the per-entry form (diary: /<user>/film/<slug>/<n>/).

Bad inputs raise IngestError(code, message) so the API returns a friendly 4xx, never a 500.
"""

import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import date

# Export members we read. ratings/diary/watched drive films; reviews adds optional review text.
_RATINGS = "ratings.csv"
_DIARY = "diary.csv"
_WATCHED = "watched.csv"
_REVIEWS = "reviews.csv"
_KNOWN_CSVS = {_RATINGS, _DIARY, _WATCHED, _REVIEWS}

_SLUG_RE = re.compile(r"/film/([^/]+)/")


class IngestError(Exception):
    """A user-facing ingestion failure. `code` is stable; `message` is friendly."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ParsedFilm:
    title: str
    year: int | None
    slug: str | None
    rating: float | None = None
    watched_at: date | None = None
    is_rewatch: bool = False
    review_text: str | None = None
    # Internal: how many diary entries referenced this film (>1 ⇒ rewatch even without the flag).
    _diary_count: int = field(default=0, repr=False)

    @property
    def lookup_key(self) -> str:
        """Stable cross-user key for the TMDB match cache: slug if we have one, else title::year."""
        if self.slug:
            return self.slug
        return f"{self.title.strip().lower()}::{self.year or ''}"


def parse_csv_rating(raw: str | None) -> float | None:
    """Export ratings are decimals in [0.5, 5.0]; snap to the nearest half-star, else None."""
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    try:
        value = float(s)
    except ValueError:
        return None
    if 0.5 <= value <= 5.0:
        return round(value * 2) / 2
    return None


def slug_from_uri(uri: str | None) -> str | None:
    if not uri:
        return None
    match = _SLUG_RE.search(uri)
    return match.group(1) if match else None


def _parse_year(raw: str | None) -> int | None:
    if not raw:
        return None
    raw = raw.strip()
    return int(raw) if raw.isdigit() and len(raw) == 4 else None


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw.strip())
    except (ValueError, TypeError):
        return None


def parse_export(data: bytes, filename: str = "") -> list[ParsedFilm]:
    """Parse the uploaded export into a de-duplicated film list. Raises IngestError on bad input."""
    if not data:
        raise IngestError("EMPTY_FILE", "The uploaded file is empty.")

    if zipfile.is_zipfile(io.BytesIO(data)):
        return _parse_zip(data)

    # Not a ZIP — accept a single bare CSV (a common thing users try), reject anything else.
    if filename.lower().endswith(".csv") or _looks_like_csv(data):
        films = _merge_rows(_read_csv(data))
        if not films:
            raise IngestError(
                "NO_FILMS",
                "That CSV has no films in it. Upload your full Letterboxd export ZIP.",
            )
        return films

    raise IngestError(
        "INVALID_FILE",
        "That doesn't look like a Letterboxd export. Upload the ZIP you got from "
        "Letterboxd → Settings → Import & Export → Export Your Data.",
    )


def _parse_zip(data: bytes) -> list[ParsedFilm]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        # Map basename → member for the CSVs we care about (members may be nested in a folder).
        members: dict[str, str] = {}
        for name in zf.namelist():
            base = name.rsplit("/", 1)[-1].lower()
            if base in _KNOWN_CSVS and base not in members:
                members[base] = name

        if not (_KNOWN_CSVS & members.keys()):
            raise IngestError(
                "NO_LETTERBOXD_CSVS",
                "That ZIP doesn't contain a Letterboxd export (no ratings.csv / diary.csv / "
                "watched.csv). Upload the export ZIP from Letterboxd.",
            )

        rows: list[dict] = []
        # Order matters for the merge: ratings (authoritative rating) → diary (watch dates,
        # rewatch) → watched (presence) → reviews (text).
        for base in (_RATINGS, _DIARY, _WATCHED, _REVIEWS):
            member = members.get(base)
            if member:
                rows.extend(_read_csv(zf.read(member), source=base))

    films = _merge_rows(rows)
    if not films:
        raise IngestError(
            "NO_FILMS",
            "No films were found in that export. It may be empty — log some films on "
            "Letterboxd and export again.",
        )
    return films


def _looks_like_csv(data: bytes) -> bool:
    try:
        head = data[:2048].decode("utf-8-sig")
    except UnicodeDecodeError:
        return False
    first_line = head.splitlines()[0] if head.splitlines() else ""
    return "," in first_line and ("Name" in first_line or "Letterboxd URI" in first_line)


def _read_csv(raw: bytes, source: str = "") -> list[dict]:
    """Decode (BOM-tolerant) and return normalized rows: lowercased keys + a `_source` tag."""
    import csv

    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict] = []
    for row in reader:
        norm = {
            (k.strip().lower() if k else ""): (v.strip() if isinstance(v, str) else v)
            for k, v in row.items()
        }
        norm["_source"] = source
        rows.append(norm)
    return rows


def _merge_rows(rows: list[dict]) -> list[ParsedFilm]:
    """Collapse rows (possibly across ratings/diary/watched/reviews) into one film each."""
    films: dict[str, ParsedFilm] = {}

    for row in rows:
        title = (row.get("name") or "").strip()
        if not title:
            continue  # a row with no film name is unusable

        slug = slug_from_uri(row.get("letterboxd uri"))
        year = _parse_year(row.get("year"))
        key = slug or f"{title.lower()}::{year or ''}"

        film = films.get(key)
        if film is None:
            film = ParsedFilm(title=title, year=year, slug=slug)
            films[key] = film
        else:
            # Backfill title/year/slug if an earlier row lacked them.
            film.year = film.year or year
            film.slug = film.slug or slug

        source = row.get("_source", "")

        # Rating: ratings.csv is authoritative; otherwise take a diary/other rating if we have none.
        rating = parse_csv_rating(row.get("rating"))
        if rating is not None:
            if source == _RATINGS or film.rating is None:
                film.rating = rating

        # Watched date: prefer "Watched Date" (diary), fall back to "Date" (logged). Keep the latest.
        watched = _parse_date(row.get("watched date")) or _parse_date(row.get("date"))
        if watched and (film.watched_at is None or watched > film.watched_at):
            film.watched_at = watched

        # Rewatch: explicit flag, or more than one diary entry for the same film.
        if source == _DIARY:
            film._diary_count += 1
        if (row.get("rewatch") or "").strip().lower() == "yes" or film._diary_count > 1:
            film.is_rewatch = True

        review = (row.get("review") or "").strip()
        if review and not film.review_text:
            film.review_text = review

    return list(films.values())

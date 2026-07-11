"""Test helpers: fixture access, in-memory ZIP builders, and a network-free TMDB stand-in."""

import io
import zipfile
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_bytes(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def build_export_zip(
    names=("ratings.csv", "diary.csv", "watched.csv", "reviews.csv"), *, subdir: str = ""
) -> bytes:
    """Build a Letterboxd-export ZIP from the committed CSV fixtures."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in names:
            arcname = f"{subdir}/{name}" if subdir else name
            zf.writestr(arcname, fixture_bytes(name))
    return buffer.getvalue()


def build_zip_from(files: dict[str, bytes]) -> bytes:
    """Build an arbitrary ZIP from {name: bytes} — used for malformed-export cases."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buffer.getvalue()


class FakeTMDB:
    """In-memory TMDB stand-in with call counters, so tests never hit the network."""

    def __init__(self, matches: dict[str, dict], details: dict[int, dict]) -> None:
        self.matches = matches            # title -> search result ({"id": ...}) or None
        self.details = details            # tmdb_id -> details dict (may include credits/keywords)
        self.search_calls = 0
        self.details_calls = 0

    @property
    def configured(self) -> bool:
        return True

    def search_movie_match(self, title: str, year: int | None) -> dict | None:
        self.search_calls += 1
        return self.matches.get(title)

    def movie_details(self, tmdb_id: int, append: str | None = None) -> dict:
        self.details_calls += 1
        return self.details.get(tmdb_id, {})

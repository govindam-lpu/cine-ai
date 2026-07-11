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


# Two clearly-separable semantic clusters, used to test the embedding taste vector + eval with real
# fastembed vectors. Cerebral sci-fi vs light romantic comedy — distant regions of embedding space.
SCIFI_TEXTS = [
    "A lone cosmonaut orbits a sentient planet that resurrects his memories and his lost love.",
    "In a decaying future, a man crosses an alien zone toward a room that grants one's deepest wish.",
    "An astronaut drifts through deep space confronting artificial intelligence and the birth of consciousness.",
    "A physicist discovers that time is collapsing and must reconcile memory, grief and quantum reality.",
    "Replicants question their own humanity in a rain-soaked city of endless neon and doubt.",
    "A linguist deciphers an alien language that unravels her perception of time and free will.",
    "Two scientists enter a simulated reality nested inside another simulation to recover a lost mind.",
    "A slow, contemplative journey across the stars meditating on solitude, entropy and remembrance.",
]

ROMCOM_TEXTS = [
    "A clumsy florist keeps bumping into the same charming stranger at every friend's wedding.",
    "Two rivals running competing bakeries fall for each other over a citywide cupcake contest.",
    "A cynical journalist pretends to date her neighbor and accidentally falls in love for real.",
    "Childhood best friends realize on the eve of one's wedding that they were meant for each other.",
    "A small-town barista and a big-city lawyer trade lives and hearts over one snowy Christmas.",
    "A matchmaker who can't find her own love keeps setting up the handsome man she secretly adores.",
    "Mixed-up dating-app messages send two strangers on a series of hilarious blind rendezvous.",
    "A woman fakes a fiancé for the holidays and hires the grumpy waiter next door to play along.",
]


# Shared writer fixtures: a fleshed-out evidence bundle + one recommended film with fired signals.
WRITER_EVIDENCE = {
    "counts": {"rated": 40, "rewatched": 3},
    "baseline_rating": 3.8,
    "genre_affinity": [{"genre": "Drama", "delta": 0.5}, {"genre": "Action", "delta": -0.4}],
    "era_affinity": [{"decade": "1960s", "delta": 0.6}],
    "crew_affinity": {"director": [{"name": "David Lean", "delta": 0.7, "n": 4}]},
    "contrarianism": {"value": 0.4},
    "obscurity_preference": {"value": -0.5},
    "patience": {"value": 0.4},
}
WRITER_FILM = {"title": "Doctor Zhivago", "year": 1965, "overview": "An epic romance across a war."}
WRITER_SIGNALS = [
    {"factor": "similarity", "strength": 0.3, "detail": "It sits close to the center of what you rate highly."},
    {"factor": "director", "strength": 0.2, "detail": "You rate David Lean's films above your average.", "name": "David Lean"},
    {"factor": "genre", "strength": 0.15, "detail": "Drama is one of your higher-rated genres.", "name": "Drama"},
]


class FakeHTTPResponse:
    """Minimal requests.Response stand-in for mocking Groq/Ollama HTTP at the transport layer."""

    def __init__(self, status_code: int = 200, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {}

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        import requests

        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def groq_payload(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def ollama_payload(content: str) -> dict:
    return {"message": {"content": content}}


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

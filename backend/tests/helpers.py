"""Test helpers: fixture access, in-memory ZIP builders, and a network-free TMDB stand-in."""

import io
import json
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

    def __init__(
        self, matches: dict[str, dict], details: dict[int, dict], discover: list[dict] | None = None
    ) -> None:
        self.matches = matches            # title -> search result ({"id": ...}) or None
        self.details = details            # tmdb_id -> details dict (may include credits/keywords)
        self.discover = discover or []    # list of {"id": ...} candidate results
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

    def discover_movies(self, params: dict) -> dict:
        # All candidates come back on page 1; later pages are empty.
        return {"results": self.discover if params.get("page", 1) == 1 else []}

    def search_keyword_ids(self, phrases: list[str]) -> list[int]:
        return []  # no keyword resolution in tests


_GENRES = ["Drama", "Science Fiction", "Thriller", "Comedy", "Romance", "War", "Crime", "History"]


def _detail(tmdb_id: int, title: str, *, year: int, genres: list[str], overview: str,
            runtime: int, votes: int, vote_avg: float, director: str) -> dict:
    return {
        "id": tmdb_id, "title": title, "release_date": f"{year}-01-01", "runtime": runtime,
        "overview": overview, "original_language": "en", "vote_average": vote_avg, "vote_count": votes,
        "genres": [{"name": g} for g in genres],
        "credits": {"crew": [{"job": "Director", "name": director}]},
        "keywords": {"keywords": [{"name": g.lower()} for g in genres]},
    }


def make_e2e_fixture():
    """Build (ratings_csv_bytes, FakeTMDB) for the full pipeline e2e: 28 rated watched films (clears
    the 25/15 gate) that all match, plus 12 unwatched discovery candidates. Deterministic."""
    watched_lines = ["Date,Name,Year,Letterboxd URI,Rating"]
    matches: dict[str, dict] = {}
    details: dict[int, dict] = {}

    for i in range(28):
        tid = 1000 + i
        title = f"Watched Film {i:02d}"
        slug = f"watched-film-{i:02d}"
        year = 1970 + (i % 40)
        genres = [_GENRES[i % len(_GENRES)], _GENRES[(i + 3) % len(_GENRES)]]
        rating = [5.0, 4.5, 4.0, 2.0, 1.5][i % 5]   # a spread so evidence has variance
        overview = f"A {genres[0].lower()} story number {i} about people and consequences."
        watched_lines.append(f"2025-01-{(i % 27) + 1:02d},{title},{year},https://letterboxd.com/film/{slug}/,{rating}")
        matches[title] = {"id": tid}
        details[tid] = _detail(tid, title, year=year, genres=genres, overview=overview,
                               runtime=90 + (i % 5) * 20, votes=200 + i * 50, vote_avg=6.0 + (i % 5) * 0.4,
                               director=f"Director {i % 6}")

    discover: list[dict] = []
    for j in range(12):
        tid = 2000 + j
        title = f"Candidate Film {j:02d}"
        genres = [_GENRES[j % len(_GENRES)], _GENRES[(j + 2) % len(_GENRES)]]
        details[tid] = _detail(tid, title, year=1980 + j, genres=genres,
                               overview=f"A {genres[0].lower()} candidate {j} exploring memory and time.",
                               runtime=100 + j * 5, votes=300 + j * 40, vote_avg=6.5 + (j % 4) * 0.5,
                               director=f"Director {j % 6}")
        discover.append({"id": tid})

    csv_bytes = ("\n".join(watched_lines) + "\n").encode("utf-8")
    return csv_bytes, FakeTMDB(matches, details, discover)


class FakeWriter:
    """Canned, deterministic writer — the pipeline's Writer seam for e2e tests (no LLM)."""

    def write_taste_summary(self, evidence: dict) -> str:
        return "You lean toward serious, character-driven films across several decades."

    def write_reason(self, evidence: dict, film: dict, signals: list[dict]) -> str:
        return f"Recommended for you because it fits your taste: {film['title']}."


def seed_ready_profile(client, monkeypatch, handle: str = "e2e") -> str:
    """Upload the e2e fixture with fakes injected and poll to a ready profile. Returns the handle."""
    import time

    import app.services.pipeline as pipeline

    csv_bytes, fake_tmdb = make_e2e_fixture()
    monkeypatch.setattr(pipeline, "make_tmdb", lambda: fake_tmdb)
    monkeypatch.setattr(pipeline, "make_writer", lambda: FakeWriter())

    resp = client.post(
        "/api/profiles/upload",
        files={"file": ("ratings.csv", csv_bytes, "text/csv")},
        data={"handle": handle},
    )
    assert resp.status_code == 202, resp.text
    job_id = resp.json()["job_id"]

    deadline = time.time() + 25
    while time.time() < deadline:
        job = client.get(f"/api/profiles/{handle}/sync/{job_id}").json()
        if job["status"] in ("complete", "failed"):
            return handle
        time.sleep(0.05)
    raise AssertionError("profile did not finish building in time")


def parse_sse(text: str) -> list[dict]:
    """Parse `data:` payloads out of an SSE body, skipping the trailing done event."""
    events = []
    for line in text.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line[len("data: "):])
            if "count" not in payload:   # skip the done event
                events.append(payload)
    return events

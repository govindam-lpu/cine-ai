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

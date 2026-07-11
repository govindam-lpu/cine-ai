"""Rate limits produce a friendly 429, never a 500."""

from app.core.ratelimit import RateLimiter
from tests.helpers import build_export_zip


def test_rate_limiter_allows_then_blocks_per_key():
    rl = RateLimiter(max_requests=2, window_seconds=100)
    assert rl.allow("a") and rl.allow("a")
    assert not rl.allow("a")          # third hit blocked
    assert rl.allow("b")              # a different key is independent


def test_rate_limiter_window_expires():
    rl = RateLimiter(max_requests=1, window_seconds=10)
    assert rl.allow("k", now=0.0)
    assert not rl.allow("k", now=5.0)
    assert rl.allow("k", now=11.0)    # window slid past → allowed again


def test_upload_over_limit_returns_429(client, monkeypatch):
    from app.api import profiles

    monkeypatch.setattr(profiles, "upload_limiter_ip", RateLimiter(max_requests=1, window_seconds=3600))

    files = {"file": ("export.zip", build_export_zip(), "application/zip")}
    first = client.post("/api/profiles/upload", files=files, data={"handle": "u1"})
    second = client.post("/api/profiles/upload", files=files, data={"handle": "u2"})

    assert first.status_code == 202
    assert second.status_code == 429
    assert second.json()["detail"]["code"] == "RATE_LIMITED"


def test_recommendations_over_limit_returns_429(client, monkeypatch):
    from app.api import profiles

    monkeypatch.setattr(profiles, "rec_limiter_ip", RateLimiter(max_requests=0, window_seconds=3600))
    resp = client.get("/api/profiles/anyone/recommendations")
    assert resp.status_code == 429
    assert resp.json()["detail"]["code"] == "RATE_LIMITED"

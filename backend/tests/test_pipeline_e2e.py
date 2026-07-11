"""The whole chain, TMDB + writer stubbed: upload → poll → profile ready → 8 unwatched recs, each
with a reason."""

from tests.helpers import make_e2e_fixture, parse_sse, seed_ready_profile


def test_upload_to_recommendations_end_to_end(client, monkeypatch):
    handle = seed_ready_profile(client, monkeypatch, handle="cinephile")

    # Profile is ready, with a written summary and computed evidence.
    profile = client.get(f"/api/profiles/{handle}")
    assert profile.status_code == 200
    body = profile.json()
    assert body["status"] == "ready"
    assert body["summary"]
    assert body["evidence"]["counts"]["rated"] == 28
    assert profile.headers.get("x-robots-tag") == "noindex, nofollow"

    # Recommendations stream: 8 films, all unwatched (candidate ids 2000+), each with a reason.
    resp = client.get(f"/api/profiles/{handle}/recommendations")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    recs = parse_sse(resp.text)
    assert len(recs) == 8
    watched_ids = set(range(1000, 1028))
    for rec in recs:
        assert rec["tmdb_id"] not in watched_ids     # never a watched film
        assert rec["tmdb_id"] >= 2000                 # a discovery candidate
        assert rec["reason"]                          # every card has prose
        assert rec["signals"]


def test_profile_404_when_never_ingested(client):
    resp = client.get("/api/profiles/nobody")
    assert resp.status_code == 404
    assert resp.json()["code"] == "PROFILE_NOT_FOUND"


def test_recommendations_before_ready_returns_building_not_empty(client, monkeypatch):
    import app.services.pipeline as pipeline
    from tests.helpers import FakeWriter

    # A below-gate upload (the 7-film zip) completes but never becomes "ready".
    _, fake = make_e2e_fixture()
    monkeypatch.setattr(pipeline, "make_tmdb", lambda: fake)
    monkeypatch.setattr(pipeline, "make_writer", lambda: FakeWriter())

    from tests.helpers import build_export_zip

    r = client.post(
        "/api/profiles/upload",
        files={"file": ("export.zip", build_export_zip(), "application/zip")},
        data={"handle": "small"},
    )
    job_id = r.json()["job_id"]
    import time

    deadline = time.time() + 20
    while time.time() < deadline:
        if client.get(f"/api/profiles/small/sync/{job_id}").json()["status"] in ("complete", "failed"):
            break
        time.sleep(0.05)

    # 7 fixture films all match the fake catalog? No — the zip titles aren't in the fake catalog,
    # so they're unmatched → below gate. Recommendations must say so, not stream an empty list.
    resp = client.get("/api/profiles/small/recommendations")
    assert resp.status_code in (409, 200)
    assert resp.json()["status"] in ("needs_more_films", "building")

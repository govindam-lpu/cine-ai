"""Upload endpoint: happy path returns a job; bad uploads return the right 4xx.

TMDB keys are blanked in tests (conftest), so the background enrichment (which TestClient runs
inline) matches nothing — every film is counted as unmatched rather than dropped, and the job
still completes. That's exactly the graceful no-keys path.
"""

import time

from tests.helpers import build_export_zip


def _upload(client, data: bytes, filename: str, handle: str | None = None):
    files = {"file": (filename, data, "application/octet-stream")}
    form = {"handle": handle} if handle is not None else None
    return client.post("/api/profiles/upload", files=files, data=form)


def _poll_until_done(client, handle, job_id, timeout=25):
    deadline = time.time() + timeout
    while time.time() < deadline:
        job = client.get(f"/api/profiles/{handle}/sync/{job_id}").json()
        if job["status"] in ("complete", "failed"):
            return job
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} did not finish in {timeout}s")


def test_upload_happy_path_returns_job_and_completes(client):
    resp = _upload(client, build_export_zip(), "letterboxd-export.zip", handle="tester")
    assert resp.status_code == 202
    body = resp.json()
    assert body["handle"] == "tester"
    assert body["job_id"]

    # Enrichment runs on the single-worker queue → poll the progress endpoint to completion.
    job = _poll_until_done(client, "tester", body["job_id"])
    assert job["status"] == "complete"
    assert job["films_total"] == 7
    assert job["films_processed"] == 7
    assert job["films_unmatched"] == 7          # no keys → unmatched, but counted not dropped
    assert job["films_matched"] == 0


def test_upload_without_handle_generates_slug(client):
    resp = _upload(client, build_export_zip(), "export.zip")
    assert resp.status_code == 202
    assert resp.json()["handle"].startswith("guest-")


def test_upload_invalid_file_returns_422(client):
    resp = _upload(client, b"\x89PNG\r\n not a csv or zip", "photo.png")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "INVALID_FILE"


def test_upload_empty_file_returns_422(client):
    resp = _upload(client, b"", "empty.csv")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "EMPTY_FILE"


def test_upload_zip_without_csvs_returns_422(client):
    from tests.helpers import build_zip_from

    resp = _upload(client, build_zip_from({"readme.txt": b"nope"}), "random.zip")
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "NO_LETTERBOXD_CSVS"


def test_job_status_unknown_returns_404(client):
    resp = client.get("/api/profiles/tester/sync/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "JOB_NOT_FOUND"


def test_sync_disabled_returns_404(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "allow_scrape_sync", False)
    resp = client.post("/api/profiles/someuser/sync")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "SYNC_DISABLED"

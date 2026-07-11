"""Profile endpoints — the full v1 surface, wired end to end with guardrails.

  POST /api/profiles/upload                     public entry: multipart CSV/ZIP → 202 {handle, job_id}
  GET  /api/profiles/{handle}/sync/{job_id}     job progress (+ queue position)
  POST /api/profiles/{handle}/sync              local-dev only: scrape → 202
  GET  /api/profiles/{handle}                   taste profile (or building/needs-more state); 404 if never ingested
  GET  /api/profiles/{handle}/recommendations   ranks fresh, streams reasons (SSE)

Guardrails: per-IP + per-handle rate limits, the single-worker ingest queue, the Groq daily budget
(friendly "at capacity" state), and noindex on the profile-facing responses.
"""

import json
import re
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.budget import budget
from app.core.config import settings
from app.core.queue import ingest_queue
from app.core.ratelimit import RateLimiter
from app.db.session import SessionLocal, get_db
from app.models.entities import IngestJob, Profile, TasteProfile
from app.schemas.ingest import JobStatusResponse, UploadResponse
from app.services.ingest import IngestError, parse_export
from app.services.pipeline import generate_recommendations, run_full_ingest
from app.services.sync import run_sync_job

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
NOINDEX = {"X-Robots-Tag": "noindex, nofollow"}

# In-process rate limiters (v1; single-worker Space). Tunable, reset between tests.
upload_limiter_ip = RateLimiter(max_requests=12, window_seconds=3600)
upload_limiter_handle = RateLimiter(max_requests=6, window_seconds=3600)
rec_limiter_ip = RateLimiter(max_requests=90, window_seconds=3600)

_NON_SLUG = re.compile(r"[^a-z0-9]+")


def sanitize_handle(raw: str | None) -> str | None:
    if not raw:
        return None
    slug = _NON_SLUG.sub("-", raw.strip().lower()).strip("-")
    return slug or None


def generate_handle(db: Session) -> str:
    while True:
        candidate = f"guest-{secrets.token_hex(4)}"
        if db.get(Profile, candidate) is None:
            return candidate


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _too_many(message: str) -> HTTPException:
    return HTTPException(status_code=429, detail={"code": "RATE_LIMITED", "message": message})


def _job_response(job: IngestJob) -> JobStatusResponse:
    position = ingest_queue.position(job.id)
    return JobStatusResponse(
        job_id=job.id,
        handle=job.profile_handle,
        source=job.source,
        status=job.status,
        step=job.step,
        queue_position=max(0, position),
        films_total=job.films_total,
        films_processed=job.films_processed,
        films_matched=job.films_matched,
        films_unmatched=job.films_unmatched,
        error_code=job.error_code,
        error_message=job.error_message,
    )


# --- upload / sync -----------------------------------------------------------


@router.post("/upload", status_code=202, response_model=UploadResponse)
async def upload_profile(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    handle: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> UploadResponse:
    if not upload_limiter_ip.allow(_client_ip(request)):
        raise _too_many("Too many uploads from your network. Try again in a little while.")

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail={"code": "FILE_TOO_LARGE", "message": "That file is too large to be a Letterboxd export."},
        )

    try:
        films = parse_export(data, file.filename or "")
    except IngestError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": exc.message})

    resolved = sanitize_handle(handle) or generate_handle(db)
    if not upload_limiter_handle.allow(resolved):
        raise _too_many("This profile was just updated. Give it a few minutes before re-uploading.")

    profile = db.get(Profile, resolved)
    if profile is None:
        profile = Profile(handle=resolved, display_name=handle.strip() if handle else None)
        db.add(profile)
        db.commit()

    job = IngestJob(
        profile_handle=resolved, source="upload", status="queued", step="Queued",
        films_total=len(films),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    ingest_queue.submit(job.id, run_full_ingest, job.id, resolved, films, "upload")
    return UploadResponse(handle=resolved, job_id=job.id)


@router.get("/{handle}/sync/{job_id}", response_model=JobStatusResponse)
def job_status(handle: str, job_id: str, db: Session = Depends(get_db)) -> JobStatusResponse:
    job = db.get(IngestJob, job_id)
    if job is None or job.profile_handle != handle:
        raise HTTPException(
            status_code=404, detail={"code": "JOB_NOT_FOUND", "message": "No such job for this profile."}
        )
    return _job_response(job)


@router.post("/{handle}/sync", status_code=202, response_model=UploadResponse)
def sync_profile(handle: str, db: Session = Depends(get_db)) -> UploadResponse:
    """Local-dev only: scrape a Letterboxd username (the handle) and run the same enrichment."""
    if not settings.allow_scrape_sync:
        raise HTTPException(
            status_code=404,
            detail={"code": "SYNC_DISABLED", "message": "Scrape sync is disabled here. Upload your export instead."},
        )
    username = sanitize_handle(handle)
    if username is None:
        raise HTTPException(
            status_code=422, detail={"code": "INVALID_HANDLE", "message": "Provide a Letterboxd username."}
        )

    if db.get(Profile, username) is None:
        db.add(Profile(handle=username, display_name=username))
        db.commit()

    job = IngestJob(profile_handle=username, source="sync", status="queued", step="Queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    ingest_queue.submit(job.id, run_sync_job, job.id, username)
    return UploadResponse(handle=username, job_id=job.id)


# --- profile + recommendations -----------------------------------------------


def _latest_job(db: Session, handle: str) -> IngestJob | None:
    return (
        db.query(IngestJob)
        .filter(IngestJob.profile_handle == handle)
        .order_by(IngestJob.created_at.desc())
        .first()
    )


def _profile_state(db: Session, handle: str):
    """(state, payload). state ∈ not_found | building | needs_more | failed | ready."""
    profile = db.get(Profile, handle)
    if profile is None:
        return "not_found", None

    tp = db.query(TasteProfile).filter_by(profile_handle=handle).first()
    if tp is not None and tp.evidence_json is not None:
        return "ready", (profile, tp)

    job = _latest_job(db, handle)
    if job is None:
        return "not_found", None
    if job.status in ("queued", "parsing", "enriching", "analyzing"):
        return "building", job
    if job.error_code == "BELOW_GATE":
        return "needs_more", job
    if job.status == "failed":
        return "failed", job
    return "building", job


@router.get("/{handle}")
def get_profile(handle: str, db: Session = Depends(get_db)) -> JSONResponse:
    state, payload = _profile_state(db, handle)

    if state == "not_found":
        return JSONResponse(
            status_code=404,
            content={"code": "PROFILE_NOT_FOUND", "message": "No profile here yet. Upload a Letterboxd export."},
            headers=NOINDEX,
        )
    if state == "building":
        return JSONResponse(
            content={"handle": handle, "status": "building", "job": _job_response(payload).model_dump()},
            headers=NOINDEX,
        )
    if state == "needs_more":
        return JSONResponse(
            content={"handle": handle, "status": "needs_more_films", "message": payload.error_message},
            headers=NOINDEX,
        )
    if state == "failed":
        return JSONResponse(
            content={"handle": handle, "status": "failed", "message": payload.error_message},
            headers=NOINDEX,
        )

    profile, tp = payload
    return JSONResponse(
        content={
            "handle": profile.handle,
            "display_name": profile.display_name,
            "status": "ready",
            "summary": tp.summary,
            "evidence": tp.evidence_json,
            "counts": tp.evidence_json.get("counts", {}),
        },
        headers=NOINDEX,
    )


def _rec_payload(rec, reason: str, at_capacity: bool) -> dict:
    v = rec.vector
    return {
        "tmdb_id": rec.tmdb_id,
        "title": rec.title,
        "year": v.release_year,
        "poster_path": v.poster_path,
        "overview": v.overview,
        "score": rec.score,
        "signals": rec.signals,
        "reason": reason,
        "at_capacity": at_capacity,
    }


@router.get("/{handle}/recommendations", response_model=None)
def get_recommendations(
    handle: str, request: Request, mood: str | None = None, limit: int = 8
) -> StreamingResponse | JSONResponse:
    if not rec_limiter_ip.allow(_client_ip(request)):
        raise _too_many("Too many requests from your network. Try again shortly.")

    limit = max(1, min(limit, 12))

    # Gate on readiness before opening a stream, so callers get a clear state, not an empty stream.
    db = SessionLocal()
    try:
        state, payload = _profile_state(db, handle)
    finally:
        db.close()

    if state != "ready":
        status = {"not_found": 404}.get(state, 409)
        body = {"handle": handle, "status": state if state != "not_found" else "not_found"}
        if state == "needs_more":
            body["status"] = "needs_more_films"
            body["message"] = payload.error_message
        elif state == "building":
            body["message"] = "Still building this profile — check back in a moment."
        elif state == "not_found":
            body["message"] = "No profile here yet."
        return JSONResponse(status_code=status, content=body, headers=NOINDEX)

    def event_stream():
        stream_db = SessionLocal()
        count = 0
        try:
            for rec, reason, at_capacity in generate_recommendations(stream_db, handle, mood, limit, budget):
                count += 1
                yield f"data: {json.dumps(_rec_payload(rec, reason, at_capacity))}\n\n"
        finally:
            stream_db.close()
        yield f"event: done\ndata: {json.dumps({'count': count})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=NOINDEX)

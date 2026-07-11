"""Profile ingestion endpoints.

  POST /api/profiles/upload                     public entry: multipart CSV/ZIP → 202 {handle, job_id}
  GET  /api/profiles/{handle}/sync/{job_id}     job progress
  POST /api/profiles/{handle}/sync              local-dev only: scrape → 202 {handle, job_id}

Both upload and sync converge on the same enrichment job.
"""

import re
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.entities import IngestJob, Profile
from app.schemas.ingest import JobStatusResponse, UploadResponse
from app.services.enrich import run_ingest_job
from app.services.ingest import IngestError, parse_export
from app.services.sync import run_sync_job

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

# Exports are tiny (a few hundred KB even for huge libraries); cap well above that.
MAX_UPLOAD_BYTES = 25 * 1024 * 1024

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


def _job_response(job: IngestJob) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=job.id,
        handle=job.profile_handle,
        source=job.source,
        status=job.status,
        step=job.step,
        films_total=job.films_total,
        films_processed=job.films_processed,
        films_matched=job.films_matched,
        films_unmatched=job.films_unmatched,
        error_code=job.error_code,
        error_message=job.error_message,
    )


@router.post("/upload", status_code=202, response_model=UploadResponse)
async def upload_profile(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    handle: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> UploadResponse:
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail={"code": "FILE_TOO_LARGE", "message": "That file is too large to be a Letterboxd export."},
        )

    # Parse synchronously so a bad upload fails fast with a friendly 4xx (no job created).
    try:
        films = parse_export(data, file.filename or "")
    except IngestError as exc:
        raise HTTPException(status_code=422, detail={"code": exc.code, "message": exc.message})

    resolved = sanitize_handle(handle)
    if resolved is None:
        resolved = generate_handle(db)

    profile = db.get(Profile, resolved)
    if profile is None:
        profile = Profile(handle=resolved, display_name=handle.strip() if handle else None)
        db.add(profile)
        db.commit()

    job = IngestJob(
        profile_handle=resolved,
        source="upload",
        status="queued",
        step="Queued",
        films_total=len(films),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_ingest_job, job.id, resolved, films, "upload")
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
def sync_profile(
    handle: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> UploadResponse:
    """Local-dev only: scrape a Letterboxd username (the handle) and run the same enrichment."""
    if not settings.allow_scrape_sync:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "SYNC_DISABLED",
                "message": "Scrape sync is disabled here. Upload your Letterboxd export instead.",
            },
        )

    username = sanitize_handle(handle)
    if username is None:
        raise HTTPException(
            status_code=422, detail={"code": "INVALID_HANDLE", "message": "Provide a Letterboxd username."}
        )

    profile = db.get(Profile, username)
    if profile is None:
        profile = Profile(handle=username, display_name=username)
        db.add(profile)
        db.commit()

    job = IngestJob(profile_handle=username, source="sync", status="queued", step="Queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(run_sync_job, job.id, username)
    return UploadResponse(handle=username, job_id=job.id)

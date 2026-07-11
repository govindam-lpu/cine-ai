import threading

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, get_db
from app.models.entities import LetterboxdProfile, ScrapeJob, User
from app.schemas.scrape import ScrapeRequest
from app.services.sync import SyncService

router = APIRouter(prefix="/scrape", tags=["scrape"])
sync_service = SyncService()


@router.post("/letterboxd")
def scrape_letterboxd(payload: ScrapeRequest, db: Session = Depends(get_db)) -> dict:
    user = db.get(User, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "User not found"})

    active = db.query(ScrapeJob).filter(ScrapeJob.user_id == user.id, ScrapeJob.status.in_(["started", "scraping", "enriching", "profiling"])).first()
    if active:
        raise HTTPException(status_code=409, detail={"code": "ALREADY_SYNCING", "message": "Sync already in progress"})

    profile = db.query(LetterboxdProfile).filter_by(user_id=user.id).first()
    if not profile:
        raise HTTPException(status_code=400, detail={"code": "PROFILE_NOT_FOUND", "message": "No linked Letterboxd profile"})

    user.sync_status = "scraping"
    job = ScrapeJob(user_id=user.id, source="letterboxd", mode=payload.mode, status="started", step="Queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    def runner() -> None:
        thread_db = SessionLocal()
        try:
            sync_service.run_letterboxd_sync(thread_db, job.id, user.id, profile.username, payload.mode)
        finally:
            thread_db.close()

    threading.Thread(target=runner, daemon=True).start()

    return {
        "success": True,
        "data": {"job_id": job.id, "status": "started", "estimated_seconds": 45},
        "error": None,
    }


@router.get("/status/{job_id}")
def scrape_status(job_id: str, db: Session = Depends(get_db)) -> dict:
    job = db.get(ScrapeJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Job not found"})

    return {
        "success": True,
        "data": {
            "job_id": job.id,
            "status": job.status,
            "progress": {
                "step": job.step,
                "films_processed": job.films_processed,
                "films_total": job.films_total,
            },
            "error": None if not job.error_code else {"code": job.error_code, "message": job.error_message},
        },
        "error": None,
    }

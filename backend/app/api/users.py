from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import LetterboxdProfile, SerializdProfile, StreamingService, TasteProfile, User, WatchHistory
from app.schemas.users import CreateUserRequest
from app.scrapers.letterboxd import LetterboxdScraper, ScrapeError

router = APIRouter(prefix="/users", tags=["users"])


@router.post("")
def create_user(payload: CreateUserRequest, db: Session = Depends(get_db)) -> dict:
    scraper = LetterboxdScraper()
    try:
        profile = scraper.preflight(payload.letterboxd_username)
    except ScrapeError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message}) from exc

    user = User(country_code=payload.country_code.upper(), preferred_format=payload.preferred_format)
    db.add(user)
    db.commit()
    db.refresh(user)

    lb_profile = LetterboxdProfile(
        user_id=user.id,
        username=payload.letterboxd_username,
        profile_url=f"https://letterboxd.com/{payload.letterboxd_username}/",
        display_name=profile.display_name,
        avatar_url=profile.avatar_url,
        is_private=profile.is_private,
        updated_at=datetime.utcnow(),
    )
    db.add(lb_profile)

    if payload.serializd_username:
        db.add(
            SerializdProfile(
                user_id=user.id,
                username=payload.serializd_username,
                profile_url=f"https://serializd.com/user/{payload.serializd_username}",
            )
        )

    db.commit()

    return {
        "success": True,
        "data": {
            "user_id": user.id,
            "letterboxd_profile": {
                "username": lb_profile.username,
                "display_name": lb_profile.display_name,
                "avatar_url": lb_profile.avatar_url,
                "is_private": lb_profile.is_private,
            },
            "sync_status": user.sync_status,
        },
        "error": None,
    }


@router.get("/{user_id}")
def get_user(user_id: str, db: Session = Depends(get_db)) -> dict:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "User not found"})

    lb = db.query(LetterboxdProfile).filter_by(user_id=user.id).first()
    sz = db.query(SerializdProfile).filter_by(user_id=user.id).first()
    watched_count = db.query(WatchHistory).filter_by(user_id=user.id).count()
    has_taste = db.query(TasteProfile).filter_by(user_id=user.id).first() is not None
    services = db.query(StreamingService).filter_by(user_id=user.id, is_active=True).all()

    return {
        "success": True,
        "data": {
            "user_id": user.id,
            "letterboxd_username": lb.username if lb else None,
            "serializd_username": sz.username if sz else None,
            "country_code": user.country_code,
            "preferred_format": user.preferred_format,
            "last_synced_at": user.last_synced_at.isoformat() if user.last_synced_at else None,
            "sync_status": user.sync_status,
            "total_films_watched": watched_count,
            "has_taste_profile": has_taste,
            "streaming_services": [{"provider_id": s.provider_id, "provider_name": s.provider_name} for s in services],
        },
        "error": None,
    }

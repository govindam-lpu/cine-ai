from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.profile import ProfileService

router = APIRouter(prefix="/profile", tags=["profile"])
profile_service = ProfileService()


@router.get("/{user_id}")
def get_profile(user_id: str, db: Session = Depends(get_db)) -> dict:
    profile = profile_service.build_profile(db, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "User not found"})
    if profile.get("not_ready"):
        raise HTTPException(status_code=409, detail={"code": "PROFILE_NOT_READY", "message": profile["reason"]})
    return {"success": True, "data": profile, "error": None}

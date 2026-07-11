from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.recommendations import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])
recommendation_service = RecommendationService()


@router.get("/{user_id}")
def get_recommendations(
    user_id: str,
    db: Session = Depends(get_db),
    limit: int = Query(default=8, ge=1, le=20),
    mood: str | None = None,
) -> dict:
    payload = recommendation_service.recommendations_for_user(db, user_id=user_id, limit=limit, mood=mood)
    if payload is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "User not found"})
    if payload.get("not_ready"):
        raise HTTPException(status_code=409, detail={"code": "INSUFFICIENT_HISTORY", "message": payload["reason"]})
    return {"success": True, "data": payload, "error": None}

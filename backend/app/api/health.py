from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"success": True, "data": {"status": "ok", "version": settings.app_version}, "error": None}

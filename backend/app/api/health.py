"""Health check endpoint."""

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness probe. Returns the running version so deploys are verifiable."""
    return {"status": "ok", "version": settings.app_version}

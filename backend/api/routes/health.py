"""Health-check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health_check() -> dict[str, str]:
    """Report whether the FastAPI backend is available."""
    return {"status": "ok", "message": "Backend is running"}

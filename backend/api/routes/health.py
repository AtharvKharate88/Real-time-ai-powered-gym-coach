"""Health-check endpoint."""

from fastapi import APIRouter, HTTPException

from database.engine import check_database_connection

router = APIRouter(tags=["health"])


@router.get("/api/health")
def health_check() -> dict[str, str]:
    """Report whether the FastAPI backend is available."""
    return {"status": "ok", "message": "Backend is running"}


@router.get("/api/health/database")
def database_health_check() -> dict[str, str]:
    """Verify the API can reach PostgreSQL without returning credentials."""
    try:
        check_database_connection()
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail="Database unavailable") from error
    return {"status": "ok", "message": "Database connection is healthy"}

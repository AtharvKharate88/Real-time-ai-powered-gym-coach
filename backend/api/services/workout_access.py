"""Request-aware access checks for in-memory workout sessions."""

from fastapi import HTTPException, Request

from .auth import optional_current_user
from .workout_sessions import WorkoutSession, session_manager


def get_request_session(session_id: str, request: Request) -> WorkoutSession:
    """Return a session only to its owner or to its anonymous creator."""
    session = session_manager.get(session_id)
    user = optional_current_user(request)
    request_user_id = user.id if user is not None else None
    if session is None or session.user_id != request_user_id:
        raise HTTPException(status_code=404, detail="Workout session not found")
    return session

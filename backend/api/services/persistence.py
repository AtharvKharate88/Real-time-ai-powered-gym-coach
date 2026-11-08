
"""FastAPI persistence helpers backed by Neon PostgreSQL."""

from datetime import datetime

from database.repositories.exercise_repository import (
    add_exercise as add_neon_exercise,
    get_anonymous_history,
    get_users_exercises,
)


def add_exercise(
    user_id: int | None,
    exercise_name: str,
    reps: int,
    sets: int,
    elapsed_seconds: int | float,
) -> None:
    """
    Persist a completed workout to Neon, keeping anonymous workouts unassigned.
    """
    add_neon_exercise(
        user_id=user_id,
        exercise_name=exercise_name,
        reps=reps,
        sets=sets,
        elapsed_seconds=float(elapsed_seconds),
    )


def get_history(user_id: int | None) -> list[dict[str, object]]:
    """Retrieve one user's history, or legacy anonymous history."""
    if user_id is None:
        return get_anonymous_history()
    entries = get_users_exercises(user_id)
    serialized = []
    for entry in entries:
        created_at = entry.get("created_at")
        serialized.append(
            {
                **entry,
                "created_at": (
                    created_at.isoformat()
                    if isinstance(created_at, datetime)
                    else str(created_at or "")
                ),
            }
        )
    return serialized

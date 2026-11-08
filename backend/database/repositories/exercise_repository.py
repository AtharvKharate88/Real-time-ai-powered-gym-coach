
"""Shared workout persistence using SQLAlchemy and Neon PostgreSQL."""

from datetime import datetime

from sqlalchemy import select

from database.session import SessionLocal
from models import Exercise


def add_exercise(
    user_id: int | None,
    exercise_name: str,
    reps: int,
    sets: int,
    elapsed_seconds: float,
    form_score: int | None = None,
    created_at: datetime | None = None,
    set_breakdown: list[int] | None = None,
) -> None:
    """Save one workout session as a separate history entry."""
    if form_score is not None and not 0 <= form_score <= 100:
        raise ValueError("form_score must be between 0 and 100")

    with SessionLocal.begin() as db:
        db.add(Exercise(
            user_id=user_id,
            exercise_name=exercise_name,
            reps=reps,
            sets=sets,
            time=float(elapsed_seconds),
            form_score=form_score,
            **({"created_at": created_at} if created_at is not None else {}),
            set_breakdown=set_breakdown,
        ))



def get_users_exercises(user_id: int) -> list[dict]:
    """Return workout history belonging to one user."""

    with SessionLocal() as db:
        workouts = db.scalars(
            select(Exercise)
            .where(Exercise.user_id == user_id)
            .order_by(Exercise.created_at.desc())
        ).all()

        return [
            {
                "id": workout.id,
                "user_id": workout.user_id,
                "exercise_name": workout.exercise_name,
                "reps": workout.reps,
                "sets": workout.sets,
                "time": workout.time,
                "form_score": workout.form_score,
                "set_breakdown": workout.set_breakdown,
                "created_at": workout.created_at,
            }
            for workout in workouts
        ]


def get_anonymous_history() -> list[dict]:
    """Return anonymous workout history for the existing API flow."""

    with SessionLocal() as db:
        workouts = db.scalars(
            select(Exercise)
            .where(Exercise.user_id.is_(None))
            .order_by(Exercise.created_at.desc())
        ).all()

        return [
            {
                "exercise_name": workout.exercise_name,
                "reps": workout.reps,
                "sets": workout.sets,
                "time": workout.time,
                "form_score": workout.form_score,
                "set_breakdown": workout.set_breakdown,
                "created_at": (
                    workout.created_at.isoformat()
                    if workout.created_at
                    else ""
                ),
            }
            for workout in workouts
        ]


"""Shared workout persistence using SQLAlchemy and Neon PostgreSQL."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from database.session import SessionLocal
from models import Exercise


def add_exercise(
    user_id: int | None,
    exercise_name: str,
    reps: int,
    sets: int,
    elapsed_seconds: float,
) -> None:
    """
    Save workout progress.

    Combine the same user's exercise entries for the current UTC day.
    A None user_id represents an anonymous FastAPI workout.
    """

    now = datetime.now(timezone.utc)
    day_start = now.replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    next_day = day_start + timedelta(days=1)

    with SessionLocal.begin() as db:
        statement = select(Exercise).where(
            Exercise.exercise_name == exercise_name,
            Exercise.created_at >= day_start,
            Exercise.created_at < next_day,
        )

        if user_id is None:
            statement = statement.where(Exercise.user_id.is_(None))
        else:
            statement = statement.where(Exercise.user_id == user_id)

        existing = db.scalar(
            statement.order_by(Exercise.created_at.desc()).limit(1)
        )

        if existing:
            existing.reps += reps
            existing.sets += sets
            existing.time += float(elapsed_seconds)
        else:
            workout = Exercise(
                user_id=user_id,
                exercise_name=exercise_name,
                reps=reps,
                sets=sets,
                time=float(elapsed_seconds),
            )
            db.add(workout)



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
                "created_at": (
                    workout.created_at.isoformat()
                    if workout.created_at
                    else ""
                ),
            }
            for workout in workouts
        ]

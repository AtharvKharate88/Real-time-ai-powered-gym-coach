"""Authenticated, monotonic workout checkpoints and idempotent completion."""
from uuid import UUID
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert

from api.schemas.workout import LocalProgress
from api.services.auth import current_user
from database.session import SessionLocal
from models import Exercise

router = APIRouter(prefix="/api/workouts/local/accounts", tags=["workouts"])


def require_owner(request: Request, account: int):
    if current_user(request).id != account:
        raise HTTPException(403, "Sign back in to the account that started this workout.")


@router.get("/{account}/drafts")
def drafts(account: int, request: Request):
    require_owner(request, account)
    with SessionLocal() as db:
        rows = db.execute(select(Exercise.client_workout_id, Exercise.progress).where(
            Exercise.user_id == account, Exercise.progress_revision > 0
        ).order_by(Exercise.id.desc())).all()
        return [{"id": identifier, "progress": progress} for identifier, progress in rows]


@router.put("/{account}/{workout_id}")
def checkpoint(account: int, workout_id: UUID, body: LocalProgress, request: Request):
    require_owner(request, account)
    samples = body.good_frames + body.warning_frames + body.incorrect_frames
    points = 100 * body.good_frames + 75 * body.warning_frames + 50 * body.incorrect_frames
    payload = body.model_dump()
    revision = body.revision if not body.finished else None if body.reps else -1
    values = dict(exercise_name=body.exercise, reps=body.reps, sets=body.reps // body.reps_per_set,
                  time=body.elapsed_seconds, form_score=round(points / samples) if samples >= 30 else None,
                  set_breakdown=[min(body.reps_per_set, body.reps-i) for i in range(0,body.reps,body.reps_per_set)],
                  progress=payload, progress_revision=revision)
    with SessionLocal.begin() as db:
        stmt = insert(Exercise).values(user_id=account, client_workout_id=str(workout_id), **values)
        # Advance a checkpoint atomically. PostgreSQL rechecks this condition under the row lock.
        checks = [
            Exercise.progress_revision > 0, Exercise.progress_revision < body.revision,
            Exercise.exercise_name == body.exercise, Exercise.reps <= body.reps,
            Exercise.time <= body.elapsed_seconds,
        ]
        for key in ("reps_per_set", "target_sets"):
            checks.append(Exercise.progress[key].as_integer() == payload[key])
        for key in ("good_frames", "warning_frames", "incorrect_frames"):
            checks.append(Exercise.progress[key].as_integer() <= payload[key])
        write = stmt.on_conflict_do_update(index_elements=["user_id", "client_workout_id"],
                  set_={k: getattr(stmt.excluded,k) for k in values}, where=and_(*checks))
        if db.scalar(write.returning(Exercise.id)) is None:
            row = db.scalars(select(Exercise).where(Exercise.user_id == account,
                             Exercise.client_workout_id == str(workout_id))).one()
            legacy_retry = row.progress is None and body.finished and all(getattr(row,k) == values[k]
                for k in ("exercise_name", "reps", "sets", "time", "form_score", "set_breakdown"))
            if row.progress != payload and not legacy_retry:
                raise HTTPException(409, "A newer, final, or conflicting checkpoint already exists.")
    return {"revision": body.revision, "finished": body.finished}


@router.get("/{account}/{workout_id}")
def saved_state(account: int, workout_id: UUID, request: Request):
    require_owner(request, account)
    with SessionLocal() as db:
        row = db.scalars(select(Exercise).where(Exercise.user_id == account,
                          Exercise.client_workout_id == str(workout_id))).one_or_none()
        if row is None:
            return {"exists": False}
        return {"exists": True, "finished": row.progress_revision in (None, -1), "progress": row.progress}


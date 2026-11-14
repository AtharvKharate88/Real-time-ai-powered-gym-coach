"""Workout session endpoints."""

from fastapi import APIRouter, Request

from ..schemas.workout import (
    CreateWorkoutRequest,
    SessionActionResponse,
    WorkoutMetricsResponse,
    WorkoutSessionResponse,
    HistoryEntry,
    ManualWorkoutRequest,
    VoiceResponse,
)
from ..services.auth import current_user, optional_current_user
from ..services.persistence import add_exercise, get_history
from ..services.workout_access import get_request_session
from ..services.workout_sessions import session_manager

router = APIRouter(prefix="/api/workouts", tags=["workouts"])


def _response(session_id: str, session) -> WorkoutSessionResponse:
    return WorkoutSessionResponse(
        session_id=session_id,
        exercise=session.exercise,
        target_sets=session.target_sets,
        reps_per_set=session.reps_per_set,
        status=session.status,
    )


def _session_set_breakdown(reps: int, reps_per_set: int) -> list[int]:
    return [min(reps_per_set, reps - offset) for offset in range(0, reps, reps_per_set)]


@router.post("/sessions", response_model=WorkoutSessionResponse, status_code=201)
def create_session(
    body: CreateWorkoutRequest, request: Request
) -> WorkoutSessionResponse:
    user = current_user(request)
    session_id, session = session_manager.create(
        body.exercise,
        body.target_sets,
        body.reps_per_set,
        user_id=user.id,
    )
    return _response(session_id, session)


@router.post("/vision/prepare")
def prepare_vision(exercise: str, request: Request) -> dict[str, bool]:
    current_user(request)
    return {"ready": session_manager.prepare_processor(exercise)}


@router.get("/sessions/{session_id}/metrics", response_model=WorkoutMetricsResponse)
def get_metrics(session_id: str, request: Request) -> WorkoutMetricsResponse:
    session = get_request_session(session_id, request)
    metrics = session.metrics()
    reps = int(metrics.get("reps", 0))
    sets_completed = min(reps // session.reps_per_set, session.target_sets)
    workout_completed = sets_completed >= session.target_sets
    if workout_completed and session.status == "running":
        session.stop()
        session.queue_voice_event("workout_completed", metrics)
        if not session.persisted and reps:
            add_exercise(
                session.user_id,
                session.exercise,
                reps,
                sets_completed,
                session.elapsed_seconds(),
                session.form_score(),
                set_breakdown=_session_set_breakdown(reps, session.reps_per_set),
            )
            session.persisted = True
    if not bool(metrics.get("pose_detected", True)):
        session.queue_voice_event(
            "no_pose_detected",
            {"issue": "No pose detected. Please step into the camera frame."},
        )
    elif sets_completed < session.target_sets:
        session.queue_voice_event("ongoing_form_check", metrics)
    return WorkoutMetricsResponse(
        session_id=session_id,
        status=session.status,
        exercise=session.exercise,
        reps=reps,
        sets_completed=sets_completed,
        current_set_reps=reps % session.reps_per_set,
        workout_completed=workout_completed,
        elapsed_seconds=session.elapsed_seconds(),
        form_score=session.form_score(),
        metrics=metrics,
    )


@router.post("/sessions/{session_id}/start", response_model=SessionActionResponse)
def start_session(session_id: str, request: Request) -> SessionActionResponse:
    session = get_request_session(session_id, request)
    session.start()
    session.queue_voice_event("workout_started", session.metrics())
    return SessionActionResponse(session_id=session_id, status="running")


@router.post("/sessions/{session_id}/resume", response_model=SessionActionResponse)
def resume_session(session_id: str, request: Request) -> SessionActionResponse:
    return start_session(session_id, request)


@router.post("/sessions/{session_id}/pause", response_model=SessionActionResponse)
def pause_session(session_id: str, request: Request) -> SessionActionResponse:
    session = get_request_session(session_id, request)
    session.pause()
    return SessionActionResponse(session_id=session_id, status="paused")


@router.post("/sessions/{session_id}/stop", response_model=SessionActionResponse)
def stop_session(session_id: str, request: Request) -> SessionActionResponse:
    session = get_request_session(session_id, request)
    session.stop()
    metrics = session.metrics()
    session.queue_voice_event("workout_completed", metrics)
    reps = int(metrics.get("reps", 0))
    sets_completed = min(reps // session.reps_per_set, session.target_sets)
    if not session.persisted and reps:
        add_exercise(
            session.user_id,
            session.exercise,
            reps,
            sets_completed,
            session.elapsed_seconds(),
            session.form_score(),
            set_breakdown=_session_set_breakdown(reps, session.reps_per_set),
        )
        session.persisted = True
    session.close()
    return SessionActionResponse(session_id=session_id, status="stopped")


@router.get("/history", response_model=list[HistoryEntry])
def history(request: Request) -> list[HistoryEntry]:
    user = optional_current_user(request)
    return [
        HistoryEntry(**entry)
        for entry in get_history(user.id if user is not None else None)
    ]


@router.post("/history/manual", response_model=HistoryEntry, status_code=201)
def add_manual_workout(body: ManualWorkoutRequest, request: Request) -> HistoryEntry:
    user = current_user(request)
    add_exercise(
        user.id,
        body.exercise_name,
        body.reps,
        body.sets,
        body.time,
        created_at=body.created_at,
    )
    return HistoryEntry(
        exercise_name=body.exercise_name,
        reps=body.reps,
        sets=body.sets,
        time=body.time,
        form_score=None,
        created_at=body.created_at.isoformat(),
    )


@router.get("/sessions/{session_id}/voice", response_model=VoiceResponse)
def get_voice(session_id: str, request: Request) -> VoiceResponse:
    session = get_request_session(session_id, request)
    pipeline = session.voice_pipeline
    if pipeline is None:
        return VoiceResponse(available=False)
    result = pipeline.get_result()
    if result is None:
        return VoiceResponse(available=True, error=bool(pipeline.get_error()))
    import base64

    audio, text = result
    return VoiceResponse(
        available=True,
        text=text,
        audio_base64=base64.b64encode(audio).decode("ascii") if audio else None,
    )

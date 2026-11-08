"""Workout session endpoints."""

from fastapi import APIRouter, HTTPException

from ..schemas.workout import (
    CreateWorkoutRequest,
    SessionActionResponse,
    WorkoutMetricsResponse,
    WorkoutSessionResponse,
    HistoryEntry,
    VoiceResponse,
)
from ..services.persistence import add_exercise, get_history
from ..services.workout_sessions import session_manager

router = APIRouter(prefix="/api/workouts", tags=["workouts"])


def _session_or_404(session_id: str):
    session = session_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Workout session not found")
    return session


def _response(session_id: str, session) -> WorkoutSessionResponse:
    return WorkoutSessionResponse(
        session_id=session_id,
        exercise=session.exercise,
        target_sets=session.target_sets,
        reps_per_set=session.reps_per_set,
        status=session.status,
    )


@router.post("/sessions", response_model=WorkoutSessionResponse, status_code=201)
def create_session(request: CreateWorkoutRequest) -> WorkoutSessionResponse:
    session_id, session = session_manager.create(
        request.exercise, request.target_sets, request.reps_per_set
    )
    return _response(session_id, session)


@router.get("/sessions/{session_id}/metrics", response_model=WorkoutMetricsResponse)
def get_metrics(session_id: str) -> WorkoutMetricsResponse:
    session = _session_or_404(session_id)
    metrics = session.metrics()
    reps = int(metrics.get("reps", 0))
    sets_completed = min(reps // session.reps_per_set, session.target_sets)
    workout_completed = sets_completed >= session.target_sets
    if workout_completed and session.status == "running":
        session.stop()
        session.queue_voice_event("workout_completed", metrics)
        if not session.persisted and reps:
            add_exercise(
                session.exercise,
                reps,
                sets_completed,
                session.elapsed_seconds(),
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
        metrics=metrics,
    )


@router.post("/sessions/{session_id}/start", response_model=SessionActionResponse)
def start_session(session_id: str) -> SessionActionResponse:
    session = _session_or_404(session_id)
    session.start()
    session.queue_voice_event("workout_started", session.metrics())
    return SessionActionResponse(session_id=session_id, status="running")


@router.post("/sessions/{session_id}/resume", response_model=SessionActionResponse)
def resume_session(session_id: str) -> SessionActionResponse:
    return start_session(session_id)


@router.post("/sessions/{session_id}/pause", response_model=SessionActionResponse)
def pause_session(session_id: str) -> SessionActionResponse:
    session = _session_or_404(session_id)
    session.pause()
    return SessionActionResponse(session_id=session_id, status="paused")


@router.post("/sessions/{session_id}/stop", response_model=SessionActionResponse)
def stop_session(session_id: str) -> SessionActionResponse:
    session = _session_or_404(session_id)
    session.stop()
    metrics = session.metrics()
    session.queue_voice_event("workout_completed", metrics)
    reps = int(metrics.get("reps", 0))
    sets_completed = min(reps // session.reps_per_set, session.target_sets)
    if not session.persisted and reps:
        add_exercise(
            session.exercise,
            reps,
            sets_completed,
            session.elapsed_seconds(),
        )
        session.persisted = True
    session.close()
    return SessionActionResponse(session_id=session_id, status="stopped")


@router.get("/history", response_model=list[HistoryEntry])
def history() -> list[HistoryEntry]:
    return [HistoryEntry(**entry) for entry in get_history()]


@router.get("/sessions/{session_id}/voice", response_model=VoiceResponse | None)
def get_voice(session_id: str) -> VoiceResponse | None:
    session = _session_or_404(session_id)
    pipeline = session.voice_pipeline
    if pipeline is None:
        return None
    result = pipeline.get_result()
    if result is None:
        return None
    import base64

    audio, text = result
    return VoiceResponse(
        text=text,
        audio_base64=base64.b64encode(audio).decode("ascii") if audio else None,
    )

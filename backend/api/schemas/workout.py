"""Workout and WebRTC API schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class CreateWorkoutRequest(BaseModel):
    exercise: Literal[
        "Squats",
        "Push-ups",
        "Biceps Curls (Dumbbell)",
        "Shoulder Press",
        "Lunges",
    ]
    target_sets: int = Field(ge=1, le=50)
    reps_per_set: int = Field(ge=1, le=50)


class WorkoutSessionResponse(BaseModel):
    session_id: str
    exercise: str
    target_sets: int
    reps_per_set: int
    status: Literal["ready", "running", "paused", "stopped"]


class WorkoutMetricsResponse(BaseModel):
    session_id: str
    status: Literal["ready", "running", "paused", "stopped"]
    exercise: str
    reps: int
    sets_completed: int
    current_set_reps: int
    workout_completed: bool
    elapsed_seconds: int
    metrics: dict[str, int | str | bool]


class SessionActionResponse(BaseModel):
    session_id: str
    status: Literal["running", "paused", "stopped"]


class VoiceResponse(BaseModel):
    text: str
    audio_base64: str | None = None


class HistoryEntry(BaseModel):
    exercise_name: str
    reps: int
    sets: int
    time: float
    created_at: str


class WebRTCOffer(BaseModel):
    sdp: str
    type: Literal["offer"]


class WebRTCAnswer(BaseModel):
    sdp: str
    type: Literal["answer"]

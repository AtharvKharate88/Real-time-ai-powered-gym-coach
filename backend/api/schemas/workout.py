"""Workout and WebRTC API schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LocalSquatSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    reps: int = Field(ge=1, le=2500)
    reps_per_set: int = Field(ge=1, le=50)
    target_sets: int = Field(ge=1, le=50)
    elapsed_seconds: int = Field(ge=0, le=86400)
    good_frames: int = Field(ge=0, le=2_000_000)
    warning_frames: int = Field(ge=0, le=2_000_000)

    @model_validator(mode="after")
    def within_target(self):
        if self.reps > self.target_sets * self.reps_per_set:
            raise ValueError("Rep count exceeds the configured workout")
        return self


class LocalProgress(LocalSquatSummary):
    exercise: Literal["Squats", "Push-ups", "Biceps Curls (Dumbbell)", "Shoulder Press", "Lunges"]
    reps: int = Field(ge=0, le=2500)
    incorrect_frames: int = Field(default=0, ge=0, le=2_000_000)
    revision: int = Field(ge=1, le=2_000_000_000)
    finished: bool


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
    form_score: int | None = None
    metrics: dict[str, int | str | bool]


class SessionActionResponse(BaseModel):
    session_id: str
    status: Literal["running", "paused", "stopped"]


class VoiceResponse(BaseModel):
    available: bool
    text: str | None = None
    audio_base64: str | None = None
    error: bool = False


class HistoryEntry(BaseModel):
    exercise_name: str
    reps: int
    sets: int
    time: float
    form_score: int | None = None
    set_breakdown: list[int] | None = None
    created_at: str


class ManualWorkoutRequest(BaseModel):
    exercise_name: Literal[
        "Squats",
        "Push-ups",
        "Biceps Curls (Dumbbell)",
        "Shoulder Press",
        "Lunges",
    ]
    reps: int = Field(ge=0, le=5000)
    sets: int = Field(ge=1, le=100)
    time: float = Field(ge=0, le=86400)
    created_at: datetime


class WebRTCOffer(BaseModel):
    sdp: str
    type: Literal["offer"]


class WebRTCAnswer(BaseModel):
    sdp: str
    type: Literal["answer"]


class WebRTCIceCandidate(BaseModel):
    candidate: str | None = None
    sdpMid: str | None = None
    sdpMLineIndex: int | None = None

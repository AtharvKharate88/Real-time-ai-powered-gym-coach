"""In-memory workout session management for the current API process."""

from __future__ import annotations

import threading
import time
import uuid
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.vision.excercise_video_processor import VideoProcessorClass


@dataclass
class WorkoutSession:
    exercise: str
    target_sets: int
    reps_per_set: int
    user_id: int | None = None
    processor: Any = field(default=None, init=False)
    status: str = "ready"
    peer_connection: object | None = None
    started_at: float | None = None
    paused_at: float | None = None
    elapsed_before_pause: float = 0.0
    persisted: bool = False
    voice_pipeline: Any = field(default=None, init=False)

    def ensure_processor(self) -> Any:
        if self.processor is not None:
            return self.processor
        from services.vision.excercise_video_processor import VideoProcessorClass

        self.processor = VideoProcessorClass()
        self.processor.set_exercise(self.exercise)
        return self.processor

    def metrics(self) -> dict[str, int | str | bool]:
        if self.processor is None:
            return {"pose_detected": False}
        return self.processor.get_latest_metrics() or {"pose_detected": False}

    def form_score(self) -> int | None:
        if self.processor is None:
            return None
        get_score = getattr(self.processor, "get_form_score", None)
        return get_score() if callable(get_score) else None

    def elapsed_seconds(self) -> int:
        if self.started_at is None:
            return int(self.elapsed_before_pause)
        end = self.paused_at if self.status == "paused" else time.monotonic()
        return int(self.elapsed_before_pause + end - self.started_at)

    def start(self) -> None:
        if self.status == "running":
            return
        self.started_at = time.monotonic()
        self.paused_at = None
        self.status = "running"

    def pause(self) -> None:
        if self.status == "running" and self.started_at is not None:
            self.elapsed_before_pause += time.monotonic() - self.started_at
            self.paused_at = time.monotonic()
            self.started_at = None
        self.status = "paused"

    def stop(self) -> None:
        if self.status == "running":
            self.pause()
        self.status = "stopped"

    def ensure_voice_pipeline(self) -> Any:
        if self.voice_pipeline is not None:
            return self.voice_pipeline
        import os

        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            return None
        try:
            from groq import Groq
            from services.coaching.llm import LLMCoach
            from services.coaching.tts import TextToSpeech
            from services.coaching.voice_pipeline import VoicePipeline
        except ImportError as error:
            logger.warning("Voice coaching unavailable: %s", error)
            return None

        self.voice_pipeline = VoicePipeline(
            LLMCoach(Groq(api_key=api_key, timeout=20.0)),
            TextToSpeech(),
        )
        return self.voice_pipeline

    def close(self) -> None:
        if self.peer_connection is not None:
            self.peer_connection = None
        if self.processor is not None:
            self.processor.on_ended()
        if self.voice_pipeline is not None:
            self.voice_pipeline.stop()

    def queue_voice_event(
        self, event: str, metrics: dict[str, int | str | bool]
    ) -> None:
        pipeline = self.ensure_voice_pipeline()
        if pipeline is not None:
            pipeline.process_event(event, self.exercise, metrics)


class WorkoutSessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, WorkoutSession] = {}
        self._prepared_processor: Any | None = None
        self._lock = threading.Lock()

    def prepare_processor(self, exercise: str) -> bool:
        """Load and warm pose inference while the user checks their camera."""
        with self._lock:
            if self._prepared_processor is None:
                from services.vision.excercise_video_processor import VideoProcessorClass

                self._prepared_processor = VideoProcessorClass()
            self._prepared_processor.set_exercise(exercise)
            return self._prepared_processor.warm_up()

    def create(
        self,
        exercise: str,
        target_sets: int,
        reps_per_set: int,
        user_id: int | None = None,
    ) -> tuple[str, WorkoutSession]:
        session_id = str(uuid.uuid4())
        session = WorkoutSession(exercise, target_sets, reps_per_set, user_id)
        with self._lock:
            if self._prepared_processor is not None:
                session.processor = self._prepared_processor
                session.processor.set_exercise(exercise)
                self._prepared_processor = None
            self._sessions[session_id] = session
        return session_id, session

    def get(self, session_id: str) -> WorkoutSession | None:
        with self._lock:
            return self._sessions.get(session_id)

    def remove(self, session_id: str) -> WorkoutSession | None:
        with self._lock:
            return self._sessions.pop(session_id, None)


session_manager = WorkoutSessionManager()
logger = logging.getLogger(__name__)

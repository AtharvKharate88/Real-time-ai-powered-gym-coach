import queue
import threading
import time
from services.diagnostics import log


class VoicePipeline:
    def __init__(self, llm, tts):
        self.llm = llm
        self.tts = tts
        self._tasks = queue.Queue(maxsize=1)
        self._results = queue.Queue(maxsize=1)
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._pending_events = set()
        self._last_submitted = {}
        self._last_feedback_at = 0.0
        self._last_error = None
        self._worker = threading.Thread(
            target=self._run_worker,
            name="voice-coaching-worker",
            daemon=True,
        )
        self._worker.start()
        log("[VOICE] Worker initialized")

    def _find_form_issue(self, exercise, metrics):
        structured_issue = metrics.get("form_issue")
        if isinstance(structured_issue, str) and structured_issue:
            return structured_issue
        if "issue" in metrics:
            return metrics["issue"]

        if exercise == "Squats":
            depth = metrics.get("depth_status", "")
            back_angle = metrics.get("back_angle", 180)

            if depth == "TOO HIGH":
                return "The user's squat is not deep enough — knees are not bending sufficiently."

            if isinstance(back_angle, (int, float)) and back_angle < 130:
                return "The user is leaning too far forward during the squat."

        elif exercise == "Push-ups":
            alignment = metrics.get("body_alignment", "")
            hip_status = metrics.get("hip_status", "")

            if alignment == "Poor Form":
                return "The user's body is not straight during the push-up."

            if hip_status == "SAGGING":
                return "The user's hips are sagging down during the push-up."

            if hip_status == "PIKED UP":
                return "The user's hips are too high — lower them to form a straight line."

        elif exercise == "Biceps Curls (Dumbbell)":
            swing = metrics.get("swing_status", "")
            shoulder = metrics.get("shoulder_status", "")

            if swing == "SWINGING":
                return "The user is swinging their torso during the curl — keep the body still."

            if shoulder == "ELBOW DRIFTING":
                return "The user's elbow is drifting away from their side during the curl."

        elif exercise == "Shoulder Press":
            back_arch = metrics.get("back_arch_status", "")
            if back_arch == "Excessive Arch":
                return "The user is arching their lower back excessively during the press."
            if back_arch == "Slight Arch":
                return "Slight back arch detected — encourage the user to brace their core."
        elif exercise == "Lunges":
            balance = metrics.get("balance_status", "")
            if balance == "OFF BALANCE":
                return "The user is losing balance during the lunge — feet should be hip-width apart."
        return None

    def process_event(self, event, exercise, metrics):
        issue = self._find_form_issue(exercise, metrics)
        now = time.time()
        is_major_event = event in {
            "workout_started",
            "set_completed",
            "workout_completed",
        }
        event_key = (event, exercise, issue or "")

        if not is_major_event and not issue:
            return False
        with self._lock:
            if not is_major_event and (
                now - self._last_feedback_at < 5
                or now - self._last_submitted.get(event_key, 0) < 5
            ):
                return False
            if event_key in self._pending_events:
                return False
            self._last_submitted[event_key] = now
            if not is_major_event:
                self._last_feedback_at = now
            self._pending_events.add(event_key)

        task = (event, exercise, issue, event_key)
        try:
            self._tasks.put_nowait(task)
            log(f"[VOICE] Event queued event={event} exercise={exercise}")
        except queue.Full:
            if is_major_event:
                try:
                    old_task = self._tasks.get_nowait()
                    with self._lock:
                        self._pending_events.discard(old_task[3])
                    self._tasks.task_done()
                    self._tasks.put_nowait(task)
                    log(f"[VOICE] Event queued event={event} exercise={exercise}")
                except queue.Empty:
                    with self._lock:
                        self._pending_events.discard(event_key)
                    return False
            else:
                with self._lock:
                    self._pending_events.discard(event_key)
                return False
        return True

    def _run_worker(self):
        while not self._stop_event.is_set():
            try:
                task = self._tasks.get(timeout=0.2)
            except queue.Empty:
                continue
            if task is None:
                break
            event, exercise, issue, event_key = task
            try:
                log("[VOICE] Groq request started")
                groq_started = time.perf_counter()
                text = self.llm.give_feedback(event, issue)
                log(
                    f"[VOICE] Groq request completed in "
                    f"{(time.perf_counter() - groq_started) * 1000:.0f}ms"
                )
                log("[VOICE] TTS generation started")
                tts_started = time.perf_counter()
                voice = self.tts.speak(text)
                log(
                    f"[VOICE] TTS generation completed in "
                    f"{(time.perf_counter() - tts_started) * 1000:.0f}ms"
                )
                if voice:
                    self._replace_result((voice, text))
            except Exception as error:
                with self._lock:
                    self._last_error = str(error)
                log(f"[VOICE] Worker error: {error}")
            finally:
                with self._lock:
                    self._pending_events.discard(event_key)
                self._tasks.task_done()

    def _replace_result(self, result):
        try:
            self._results.get_nowait()
        except queue.Empty:
            pass
        try:
            self._results.put_nowait(result)
        except queue.Full:
            pass

    def get_result(self):
        try:
            return self._results.get_nowait()
        except queue.Empty:
            return None

    def get_error(self):
        with self._lock:
            error = self._last_error
            self._last_error = None
            return error

    def stop(self):
        self._stop_event.set()
        try:
            self._tasks.put_nowait(None)
        except queue.Full:
            pass
        if self._worker.is_alive():
            self._worker.join(timeout=1)
        log("[VOICE] Worker stopped")

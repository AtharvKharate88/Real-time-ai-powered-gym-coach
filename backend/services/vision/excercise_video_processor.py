import os
import time
import cv2
import av
import numpy as np
import mediapipe as mp
import threading
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from detectors.squat import SquatDetector
from detectors.pushup import PushUpDetector
from detectors.biceps_curl import BicepsCurlDetector
from detectors.shoulder_press import ShoulderPressDetector
from detectors.lunges import LungesDetector
from services.config.workout_config import POSE_CONNECTIONS
from services.diagnostics import VideoStats, log
from services.vision.form_score import FormScoreAccumulator


class VideoProcessorClass:
    _INFER_MAX_WIDTH = 320

    def __init__(self):
        self._lock = threading.Lock()
        self._latest_metrics = None
        self._exercise_type = "Squats"
        self._landmarker = None
        self._landmarker_error = None
        self._frame_timestamps_ms = 0
        self._stats = VideoStats()
        self._form_score = FormScoreAccumulator()
        self._detectors = {
            "Squats": SquatDetector(),
            "Push-ups": PushUpDetector(),
            "Biceps Curls (Dumbbell)": BicepsCurlDetector(),
            "Shoulder Press": ShoulderPressDetector(),
            "Lunges": LungesDetector(),
        }
        log("[VIDEO] Processor initialized")

    def _ensure_landmarker(self):
        if self._landmarker is not None or self._landmarker_error:
            return self._landmarker
        started = time.perf_counter()
        log("[VIDEO] MediaPipe PoseLandmarker loading on video thread")
        try:
            model_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "ml_models",
                "pose_landmarker_full.task",
            )
            options = vision.PoseLandmarkerOptions(
                base_options=python.BaseOptions(model_asset_path=model_path),
                running_mode=vision.RunningMode.VIDEO,
                min_pose_detection_confidence=0.7,
                min_pose_presence_confidence=0.7,
                min_tracking_confidence=0.7,
                output_segmentation_masks=False,
            )
            self._landmarker = vision.PoseLandmarker.create_from_options(options)
            log(
                f"[VIDEO] MediaPipe PoseLandmarker ready in "
                f"{(time.perf_counter() - started) * 1000:.0f}ms"
            )
        except Exception as error:
            self._landmarker_error = str(error)
            log(f"[VIDEO] MediaPipe PoseLandmarker failed to load: {error}")
        return self._landmarker

    def warm_up(self):
        """Load the pose model before video frames begin processing."""
        return self._ensure_landmarker() is not None

    def set_latest_metrics(self, metrics):
        with self._lock:
            self._latest_metrics = metrics.copy()

    def get_latest_metrics(self):
        with self._lock:
            return None if self._latest_metrics is None else self._latest_metrics.copy()

    def get_form_score(self) -> int | None:
        return self._form_score.get_score()

    def set_exercise(self, exercise_type):
        with self._lock:
            self._exercise_type = exercise_type

    def get_exercise(self):
        with self._lock:
            return self._exercise_type

    def _next_timestamp_ms(self):
        frame_ms = int(time.monotonic() * 1000)
        if frame_ms <= self._frame_timestamps_ms:
            frame_ms = self._frame_timestamps_ms + 1
        self._frame_timestamps_ms = frame_ms
        return frame_ms

    def _draw_skeleton(self, img, landmarks):
        h, w = img.shape[:2]

        for start_idx, end_idx in POSE_CONNECTIONS:
            p1 = landmarks[start_idx]
            p2 = landmarks[end_idx]

            if p1.visibility > 0.7 and p2.visibility > 0.7:
                cv2.line(
                    img,
                    (int(p1.x * w), int(p1.y * h)),
                    (int(p2.x * w), int(p2.y * h)),
                    (0, 255, 0),
                    8
                )

        for lm in landmarks:
            if lm.visibility > 0.7:
                cv2.circle(
                    img,
                    (int(lm.x * w), int(lm.y * h)),
                    8,
                    (255, 0, 0),
                    -1
                )

    def _draw_no_pose_warnings(self, img):
        cv2.putText(
            img,
            "NO POSE DETECTED",
            (30, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        cv2.putText(
            img,
            "PLEASE FACE THE CAMERA",
            (30, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

    def _draw_overlays(self, img, metrics, ex_type):
        if ex_type == "Squats":
            self._draw_squats_overlays(img, metrics)
        elif ex_type == "Push-ups":
            self._draw_pushup_overlays(img, metrics)
        elif ex_type == "Biceps Curls (Dumbbell)":
            self._draw_curl_overlays(img, metrics)
        elif ex_type == "Shoulder Press":
            self._draw_press_overlays(img, metrics)
        elif ex_type == "Lunges":
            self._draw_lunge_overlays(img, metrics)

    def _draw_squats_overlays(self, img, metrics):
        h, _ = img.shape[:2]
        cv2.putText(
            img,
            f"DEPTH: {metrics['depth_status']}",
            (20, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

    def _draw_pushup_overlays(self, img, metrics):
        h, _ = img.shape[:2]
        cv2.putText(
            img,
            f"BODY: {metrics['body_alignment']} | HIP: {metrics['hip_status']}",
            (20, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

    def _draw_curl_overlays(self, img, metrics):
        h, _ = img.shape[:2]
        cv2.putText(
            img,
            f"SWING: {metrics['swing_status']}",
            (20, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

    def _draw_press_overlays(self, img, metrics):
        h, _ = img.shape[:2]
        cv2.putText(
            img,
            f"EXT: {metrics['extension_status']} | BACK: {metrics['back_arch_status']}",
            (20, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

    def _draw_lunge_overlays(self, img, metrics):
        h, _ = img.shape[:2]
        cv2.putText(
            img,
            f"BALANCE: {metrics['balance_status']}",
            (20, h - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )

    async def recv_queued(self, frames):
        dropped = max(0, len(frames) - 1)
        latest = frames[-1]
        processed = self.recv(latest, dropped=dropped)
        return [processed]

    def recv(self, frame, dropped=0):
        recv_started = time.perf_counter()
        image = np.asarray(
            cv2.flip(frame.to_ndarray(format="bgr24"), 1),
            dtype=np.uint8
        )
        landmarker = self._ensure_landmarker()
        infer_ms = 0.0
        detect_ms = 0.0
        if landmarker is None:
            if self._landmarker_error:
                self._draw_no_pose_warnings(image)
            else:
                cv2.putText(
                    image,
                    "LOADING POSE MODEL",
                    (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )
            self.set_latest_metrics({
                "pose_detected": False,
                "pose_status": "unavailable" if self._landmarker_error else "loading",
            })
        else:
            infer_image = image
            height, width = image.shape[:2]
            if width > self._INFER_MAX_WIDTH:
                scale = self._INFER_MAX_WIDTH / float(width)
                infer_image = cv2.resize(
                    image,
                    (int(width * scale), int(height * scale)),
                    interpolation=cv2.INTER_AREA,
                )
            rgb = cv2.cvtColor(infer_image, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            timestamp_ms = self._next_timestamp_ms()
            infer_started = time.perf_counter()
            try:
                result = landmarker.detect_for_video(mp_image, timestamp_ms)
            except Exception as error:
                log(f"[VIDEO] MediaPipe inference failed: {error}")
                latest_metrics = self.get_latest_metrics() or {}
                latest_metrics.update({"pose_detected": False, "pose_status": "error"})
                self.set_latest_metrics(latest_metrics)
                recv_ms = (time.perf_counter() - recv_started) * 1000
                self._stats.record(recv_ms, 0.0, 0.0, dropped)
                return av.VideoFrame.from_ndarray(image, format="bgr24")
            infer_ms = (time.perf_counter() - infer_started) * 1000
            if result.pose_landmarks:
                landmarks = result.pose_landmarks[0]
                self._draw_skeleton(image, landmarks)
                ex_type = self.get_exercise()
                detector = self._detectors.get(ex_type)
                if detector:
                    detect_started = time.perf_counter()
                    metrics = detector.process(landmarks)
                    detect_ms = (time.perf_counter() - detect_started) * 1000
                    metrics["pose_detected"] = True
                    metrics["pose_status"] = "detected"
                    self._form_score.record(metrics)
                    self._draw_overlays(image, metrics, ex_type)
                    self.set_latest_metrics(metrics)
            else:
                self._draw_no_pose_warnings(image)
                latest_metrics = self.get_latest_metrics() or {}
                latest_metrics["pose_detected"] = False
                latest_metrics["pose_status"] = "not_detected"
                self.set_latest_metrics(latest_metrics)
        recv_ms = (time.perf_counter() - recv_started) * 1000
        self._stats.record(recv_ms, infer_ms, detect_ms, dropped)
        return av.VideoFrame.from_ndarray(image, format="bgr24")

    def on_ended(self):
        log("[VIDEO] Processor stopped")
        if self._landmarker is not None:
            closer = getattr(self._landmarker, "close", None)
            if callable(closer):
                closer()
            self._landmarker = None

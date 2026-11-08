"""Frame-weighted, estimated coaching scores from valid detector feedback."""

import threading
from collections.abc import Mapping


class FormScoreAccumulator:
    """Average detector statuses, ignoring frames without valid movement data.

    A valid frame with no tracked issue contributes 100 points, a warning 75,
    and an incorrect-form result 50. The score remains unavailable until the
    minimum number of valid frames has been observed.
    """

    FRAME_SCORES = {"good": 100, "warning": 75, "incorrect": 50}

    def __init__(self, min_samples: int = 30) -> None:
        self.min_samples = min_samples
        self._score_total = 0
        self._sample_count = 0
        self._lock = threading.Lock()

    def record(self, metrics: Mapping[str, object]) -> None:
        if metrics.get("movement_valid") is not True:
            return
        frame_score = self.FRAME_SCORES.get(str(metrics.get("form_status")))
        if frame_score is None:
            return
        with self._lock:
            self._score_total += frame_score
            self._sample_count += 1

    def get_score(self) -> int | None:
        with self._lock:
            if self._sample_count < self.min_samples:
                return None
            return round(self._score_total / self._sample_count)

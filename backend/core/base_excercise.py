from abc import ABC,abstractmethod
import math

class BaseExercise(ABC):
    REP_STAGE_CONFIRM_FRAMES = 2

    def __init__(self):
        self.reps=0
        self.stage=None
        self._pending_rep_stage = None
        self._pending_rep_stage_frames = 0
        self._rep_armed = False

    def reset_rep_tracking(self):
        self.reps = 0
        self.stage = None
        self._pending_rep_stage = None
        self._pending_rep_stage_frames = 0
        self._rep_armed = False

    def update_rep_stage(
        self,
        angle,
        *,
        low_threshold,
        high_threshold,
        low_stage,
        high_stage,
        count_stage,
    ):
        """Require a stable threshold crossing before accepting a rep stage."""
        if angle <= low_threshold:
            candidate = low_stage
        elif angle >= high_threshold:
            candidate = high_stage
        else:
            candidate = None

        if candidate is None or candidate == self.stage:
            self._pending_rep_stage = None
            self._pending_rep_stage_frames = 0
            return

        if candidate == self._pending_rep_stage:
            self._pending_rep_stage_frames += 1
        else:
            self._pending_rep_stage = candidate
            self._pending_rep_stage_frames = 1

        if self._pending_rep_stage_frames >= self.REP_STAGE_CONFIRM_FRAMES:
            if candidate == count_stage:
                if self._rep_armed:
                    self.reps += 1
                self._rep_armed = False
            else:
                self._rep_armed = True
            self.stage = candidate
            self._pending_rep_stage = None
            self._pending_rep_stage_frames = 0

    def calculate_angle(self, a, b, c):
        ax, ay = a[0] - b[0], a[1] - b[1]
        cx, cy = c[0] - b[0], c[1] - b[1]
        dot = ax * cx + ay * cy
        mag_a = math.sqrt(ax ** 2 + ay ** 2)
        mag_c = math.sqrt(cx ** 2 + cy ** 2)

        if mag_a * mag_c == 0:
            return 0.0
        cos_angle = max(-1.0, min(1.0, dot / (mag_a * mag_c)))
        return math.degrees(math.acos(cos_angle))

    def get_point(self, landmarks, idx):
        p = landmarks[idx]
        return (p.x, p.y)

    def add_feedback(
        self,
        metrics,
        *,
        movement_valid,
        feedback_valid=None,
        confidence_values,
        previous_reps,
        issues=(),
        severity="warning",
    ):
        # Each exercise defines the landmark set required for its movement.
        confidence = min(confidence_values, default=0.0)
        if feedback_valid is None:
            feedback_valid = movement_valid
        if not movement_valid or (not feedback_valid and not issues):
            status, priority, issue_text = "waiting", "waiting", ""
        elif issues:
            status = severity if severity in {"warning", "incorrect"} else "warning"
            priority = "high" if status == "incorrect" else "medium"
            issue_text = "; ".join(issues)
        else:
            status, priority, issue_text = "good", "positive", ""

        metrics.update({
            "exercise_stage": self.stage or "ready",
            "rep_completed": self.reps > previous_reps,
            "movement_valid": bool(movement_valid),
            "pose_confidence": int(round(max(0.0, min(1.0, confidence)) * 100)),
            "form_status": status,
            "feedback_priority": priority,
            "form_issue": issue_text,
        })
        return metrics

    @abstractmethod
    def process(self, landmarks):
        pass

    @abstractmethod
    def reset(self):
        pass


BaseExcercise = BaseExercise

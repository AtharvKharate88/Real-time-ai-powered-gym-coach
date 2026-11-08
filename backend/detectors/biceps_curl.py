import math
from core.base_excercise import BaseExercise

class BicepsCurlDetector(BaseExercise):
    UP_THRESHOLD = 50
    DOWN_THRESHOLD = 160
    MIN_VISIBILITY = 0.7
    ELBOW_DRIFT_TOLERANCE = 0.06
    SWING_THRESHOLD = 15

    LEFT_SHOULDER = 11
    LEFT_ELBOW = 13
    LEFT_WRIST = 15
    RIGHT_SHOULDER = 12
    RIGHT_ELBOW = 14
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24

    def __init__(self):
        super().__init__()
        self._shoulder_x_baseline = None

    def reset(self) -> None:
        self.reset_rep_tracking()
        self._shoulder_x_baseline = None

    def process(self, landmarks) -> dict:
        previous_reps = self.reps
        left_vis = landmarks[self.LEFT_ELBOW].visibility
        right_vis = landmarks[self.RIGHT_ELBOW].visibility

        left_visible = all(landmarks[index].visibility > self.MIN_VISIBILITY for index in (self.LEFT_SHOULDER, self.LEFT_ELBOW, self.LEFT_WRIST))
        right_visible = all(landmarks[index].visibility > self.MIN_VISIBILITY for index in (self.RIGHT_SHOULDER, self.RIGHT_ELBOW, self.RIGHT_WRIST))
        left_score = min(landmarks[index].visibility for index in (self.LEFT_SHOULDER, self.LEFT_ELBOW, self.LEFT_WRIST))
        right_score = min(landmarks[index].visibility for index in (self.RIGHT_SHOULDER, self.RIGHT_ELBOW, self.RIGHT_WRIST))
        if left_visible and right_visible:
            use_left = left_score >= right_score
        elif left_visible:
            use_left = True
        elif right_visible:
            use_left = False
        else:
            use_left = left_score >= right_score

        if use_left:
            shoulder_idx = self.LEFT_SHOULDER
            elbow_idx = self.LEFT_ELBOW
            wrist_idx = self.LEFT_WRIST
        else:
            shoulder_idx = self.RIGHT_SHOULDER
            elbow_idx = self.RIGHT_ELBOW
            wrist_idx = self.RIGHT_WRIST

        elbow_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, elbow_idx),
            self.get_point(landmarks, wrist_idx),
        )

        key_landmarks_visible = left_visible if use_left else right_visible

        if key_landmarks_visible:
            self.update_rep_stage(
                elbow_angle,
                low_threshold=self.UP_THRESHOLD,
                high_threshold=self.DOWN_THRESHOLD,
                low_stage="up",
                high_stage="down",
                count_stage="down",
            )

        shoulder_x = landmarks[shoulder_idx].x
        elbow_x = landmarks[elbow_idx].x
        elbow_drift = abs(elbow_x - shoulder_x)

        if not key_landmarks_visible:
            shoulder_status = "N/A"
        elif elbow_drift <= self.ELBOW_DRIFT_TOLERANCE:
            shoulder_status = "STABLE"
        else:
            shoulder_status = "ELBOW DRIFTING"

        shoulder_mid_x = (landmarks[self.LEFT_SHOULDER].x + landmarks[self.RIGHT_SHOULDER].x) / 2
        shoulder_mid_y = (landmarks[self.LEFT_SHOULDER].y + landmarks[self.RIGHT_SHOULDER].y) / 2

        hip_mid_x = (landmarks[self.LEFT_HIP].x + landmarks[self.RIGHT_HIP].x) / 2
        hip_mid_y = (landmarks[self.LEFT_HIP].y + landmarks[self.RIGHT_HIP].y) / 2

        dx = shoulder_mid_x - hip_mid_x
        dy = shoulder_mid_y - hip_mid_y

        torso_angle_from_vertical = self._safe_angle(dx, dy)

        torso_landmarks_visible = all(
            landmarks[index].visibility > self.MIN_VISIBILITY
            for index in (self.LEFT_SHOULDER, self.RIGHT_SHOULDER, self.LEFT_HIP, self.RIGHT_HIP)
        )
        if not torso_landmarks_visible:
            swing_status = "N/A"
        elif torso_angle_from_vertical <= self.SWING_THRESHOLD:
            swing_status = "NO SWING"
        else:
            swing_status = "SWINGING"
        #while swinging the torso shouldnt bend toward dumble
        result = {
            "reps": self.reps,
            "elbow_angle": int(elbow_angle) if key_landmarks_visible else "N/A",
            "shoulder_status": shoulder_status,
            "swing_status": swing_status,
            "landmarks_visible": key_landmarks_visible,
        }
        issues = []
        if key_landmarks_visible:
            if shoulder_status == "ELBOW DRIFTING":
                issues.append("Keep your elbow close to your side")
            if swing_status == "SWINGING":
                issues.append("Avoid swinging your torso")
        selected_indices = (shoulder_idx, elbow_idx, wrist_idx)
        return self.add_feedback(
            result,
            movement_valid=key_landmarks_visible,
            feedback_valid=key_landmarks_visible and torso_landmarks_visible,
            confidence_values=[landmarks[index].visibility for index in selected_indices],
            previous_reps=previous_reps,
            issues=issues,
        )

    def _safe_angle(self, dx, dy):
        return math.degrees(math.atan2(abs(dx), abs(dy)))


from core.base_excercise import BaseExercise

class LungesDetector(BaseExercise):
    DOWN_THRESHOLD = 100
    UP_THRESHOLD = 160
    MIN_VISIBILITY = 0.7
    BALANCE_TOLERANCE = 0.10

    LEFT_HIP = 23
    LEFT_KNEE = 25
    LEFT_ANKLE = 27
    RIGHT_HIP = 24
    RIGHT_KNEE = 26
    RIGHT_ANKLE = 28
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12

    def __init__(self):
        super().__init__()

    def reset(self) -> None:
        self.reset_rep_tracking()

    def process(self, landmarks) -> dict:
        previous_reps = self.reps
        left_knee_angle = self.calculate_angle(
            self.get_point(landmarks, self.LEFT_HIP),
            self.get_point(landmarks, self.LEFT_KNEE),
            self.get_point(landmarks, self.LEFT_ANKLE),
        )

        right_knee_angle = self.calculate_angle(
            self.get_point(landmarks, self.RIGHT_HIP),
            self.get_point(landmarks, self.RIGHT_KNEE),
            self.get_point(landmarks, self.RIGHT_ANKLE),
        )

        left_visible = all(
            landmarks[index].visibility > self.MIN_VISIBILITY
            for index in (self.LEFT_HIP, self.LEFT_KNEE, self.LEFT_ANKLE)
        )
        right_visible = all(
            landmarks[index].visibility > self.MIN_VISIBILITY
            for index in (self.RIGHT_HIP, self.RIGHT_KNEE, self.RIGHT_ANKLE)
        )

        if left_visible and right_visible:
            use_left = left_knee_angle <= right_knee_angle
        elif left_visible:
            use_left = True
        elif right_visible:
            use_left = False
        else:
            use_left = left_knee_angle <= right_knee_angle

        if use_left:
            front_knee_angle = left_knee_angle
            front_hip_idx, front_knee_idx, front_ankle_idx = self.LEFT_HIP, self.LEFT_KNEE, self.LEFT_ANKLE
            shoulder_idx_for_torso = self.LEFT_SHOULDER
            key_landmarks_visible = left_visible
        else:
            front_knee_angle = right_knee_angle
            front_hip_idx, front_knee_idx, front_ankle_idx = self.RIGHT_HIP, self.RIGHT_KNEE, self.RIGHT_ANKLE
            shoulder_idx_for_torso = self.RIGHT_SHOULDER
            key_landmarks_visible = right_visible

        if key_landmarks_visible:
            self.update_rep_stage(
                front_knee_angle,
                low_threshold=self.DOWN_THRESHOLD,
                high_threshold=self.UP_THRESHOLD,
                low_stage="down",
                high_stage="up",
                count_stage="up",
            )

        torso_visible = key_landmarks_visible and landmarks[shoulder_idx_for_torso].visibility > self.MIN_VISIBILITY
        torso_angle = (
            int(self.calculate_angle(
                self.get_point(landmarks, shoulder_idx_for_torso),
                self.get_point(landmarks, front_hip_idx),
                self.get_point(landmarks, front_knee_idx),
            ))
            if torso_visible
            else "N/A"
        )

        balance_landmarks = (self.LEFT_SHOULDER, self.RIGHT_SHOULDER, self.LEFT_HIP, self.RIGHT_HIP)
        if all(landmarks[index].visibility > self.MIN_VISIBILITY for index in balance_landmarks):
            shoulder_mid_x = (landmarks[self.LEFT_SHOULDER].x + landmarks[self.RIGHT_SHOULDER].x) / 2
            hip_mid_x = (landmarks[self.LEFT_HIP].x + landmarks[self.RIGHT_HIP].x) / 2
            lateral_offset = abs(shoulder_mid_x - hip_mid_x)
            balance_status = "BALANCED" if lateral_offset <= self.BALANCE_TOLERANCE else "OFF BALANCE"
        else:
            balance_status = "N/A"

        result = {
            "reps": self.reps,
            "front_knee_angle": int(front_knee_angle) if key_landmarks_visible else "N/A",
            "torso_angle": torso_angle,
            "balance_status": balance_status,
            "landmarks_visible": key_landmarks_visible,
        }
        issues = ["Keep your balance and stance steady"] if key_landmarks_visible and balance_status == "OFF BALANCE" else []
        selected_indices = (front_hip_idx, front_knee_idx, front_ankle_idx)
        return self.add_feedback(
            result,
            movement_valid=key_landmarks_visible,
            feedback_valid=key_landmarks_visible and torso_visible and balance_status != "N/A",
            confidence_values=[landmarks[index].visibility for index in selected_indices],
            previous_reps=previous_reps,
            issues=issues,
        )

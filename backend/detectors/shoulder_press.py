from core.base_excercise import BaseExercise


class ShoulderPressDetector(BaseExercise):
    UP_THRESHOLD = 160
    DOWN_THRESHOLD = 90
    MIN_VISIBILITY = 0.7

    LEFT_SHOULDER = 11
    LEFT_ELBOW = 13
    LEFT_WRIST = 15
    RIGHT_SHOULDER = 12
    RIGHT_ELBOW = 14
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_KNEE = 25
    RIGHT_KNEE = 26

    def __init__(self):
        super().__init__()

    def reset(self) -> None:
        self.reset_rep_tracking()

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
            hip_idx = self.LEFT_HIP
            knee_idx = self.LEFT_KNEE
        else:
            shoulder_idx = self.RIGHT_SHOULDER
            elbow_idx = self.RIGHT_ELBOW
            wrist_idx = self.RIGHT_WRIST
            hip_idx = self.RIGHT_HIP
            knee_idx = self.RIGHT_KNEE
        #calculate elbow angle
        elbow_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, elbow_idx),
            self.get_point(landmarks, wrist_idx),
        )

        key_landmarks_visible = left_visible if use_left else right_visible

        if key_landmarks_visible:
            self.update_rep_stage(
                elbow_angle,
                low_threshold=self.DOWN_THRESHOLD,
                high_threshold=self.UP_THRESHOLD,
                low_stage="down",
                high_stage="up",
                count_stage="down",
            )

        if not key_landmarks_visible:
            extension_status = "N/A"
        elif elbow_angle >= self.UP_THRESHOLD:
            extension_status = "FULL EXTENSION"
        elif elbow_angle >= 130:
            extension_status = "NEARLY EXTENDED"
        elif elbow_angle >= self.DOWN_THRESHOLD:
            extension_status = "PRESSING"
        else:
            extension_status = "START POSITION"
        #back angle metrics
        back_visible = all(landmarks[index].visibility > self.MIN_VISIBILITY for index in (shoulder_idx, hip_idx, knee_idx))
        back_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, hip_idx),
            self.get_point(landmarks, knee_idx),
        ) if back_visible else None

        if back_angle is None:
            back_arch_status = "N/A"
        elif back_angle >= 160:
            back_arch_status = "Neutral"
        elif back_angle >= 140:
            back_arch_status = "Slight Arch"
        else:
            back_arch_status = "Excessive Arch"

        result = {
            "reps": self.reps,
            "elbow_angle": int(elbow_angle) if key_landmarks_visible else "N/A",
            "extension_status": extension_status,
            "back_arch_status": back_arch_status,
            "landmarks_visible": key_landmarks_visible,
        }
        issues = []
        severity = "warning"
        if key_landmarks_visible:
            if back_arch_status == "Slight Arch":
                issues.append("Brace your core to reduce back arch")
            elif back_arch_status == "Excessive Arch":
                issues.append("Avoid arching your lower back")
                severity = "incorrect"
        selected_indices = (shoulder_idx, elbow_idx, wrist_idx)
        return self.add_feedback(
            result,
            movement_valid=key_landmarks_visible,
            feedback_valid=key_landmarks_visible and back_visible,
            confidence_values=[landmarks[index].visibility for index in selected_indices],
            previous_reps=previous_reps,
            issues=issues,
            severity=severity,
        )


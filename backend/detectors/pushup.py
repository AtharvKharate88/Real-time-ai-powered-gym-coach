from core.base_excercise import BaseExercise

class PushUpDetector(BaseExercise):
    DOWN_THRESHOLD = 90
    UP_THRESHOLD = 160
    MIN_VISIBILITY = 0.7
    HIP_SAG_TOLERANCE = 0.08

    LEFT_SHOULDER = 11
    LEFT_ELBOW = 13
    LEFT_WRIST = 15
    RIGHT_SHOULDER = 12
    RIGHT_ELBOW = 14
    RIGHT_WRIST = 16
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_ANKLE = 27
    RIGHT_ANKLE = 28

    def __init__(self):
        super().__init__()

    def reset(self) -> None:
        self.reset_rep_tracking()

    def process(self, landmarks) -> dict:
        previous_reps = self.reps
        left_indices = (self.LEFT_SHOULDER, self.LEFT_ELBOW, self.LEFT_WRIST, self.LEFT_HIP, self.LEFT_ANKLE)
        right_indices = (self.RIGHT_SHOULDER, self.RIGHT_ELBOW, self.RIGHT_WRIST, self.RIGHT_HIP, self.RIGHT_ANKLE)
        left_score = min(landmarks[index].visibility for index in left_indices)
        right_score = min(landmarks[index].visibility for index in right_indices)
        left_visible = left_score > self.MIN_VISIBILITY
        right_visible = right_score > self.MIN_VISIBILITY

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
            ankle_idx = self.LEFT_ANKLE
        else:
            shoulder_idx = self.RIGHT_SHOULDER
            elbow_idx = self.RIGHT_ELBOW
            wrist_idx = self.RIGHT_WRIST
            hip_idx = self.RIGHT_HIP
            ankle_idx = self.RIGHT_ANKLE

        elbow_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, elbow_idx),
            self.get_point(landmarks, wrist_idx),
        )

        body_angle = self.calculate_angle(
            self.get_point(landmarks, shoulder_idx),
            self.get_point(landmarks, hip_idx),
            self.get_point(landmarks, ankle_idx),
        )

        shoulder_y = landmarks[shoulder_idx].y
        ankle_y = landmarks[ankle_idx].y
        hip_y = landmarks[hip_idx].y

        expected_hip_y = (shoulder_y + ankle_y) / 2
        hip_deviation = hip_y - expected_hip_y
        #hip shouldnt bend during deviation
        key_landmarks_visible = left_visible if use_left else right_visible
        
        if key_landmarks_visible:
            self.update_rep_stage(
                elbow_angle,
                low_threshold=self.DOWN_THRESHOLD,
                high_threshold=self.UP_THRESHOLD,
                low_stage="down",
                high_stage="up",
                count_stage="up",
            )

        if not key_landmarks_visible:
            body_alignment = "N/A"
            hip_status = "N/A"
        else:
            if body_angle > 160:
                body_alignment = "Straight"
            elif body_angle > 140:
                body_alignment = "Slight Bend"
            else:
                body_alignment = "Poor Form"
            if abs(hip_deviation) <= self.HIP_SAG_TOLERANCE:
                hip_status = "LEVEL"
            elif hip_deviation > 0:
                hip_status = "SAGGING"
            else:
                hip_status = "PIKED UP"

        result = {
            "reps": self.reps,
            "elbow_angle": int(elbow_angle) if key_landmarks_visible else "N/A",
            "body_alignment": body_alignment,
            "hip_status": hip_status,
            "landmarks_visible": key_landmarks_visible,
        }
        issues = []
        severity = "warning"
        if key_landmarks_visible:
            if body_alignment == "Slight Bend":
                issues.append("Keep your body aligned")
            elif body_alignment == "Poor Form":
                issues.append("Keep your body in a straight line")
                severity = "incorrect"
            if hip_status in {"SAGGING", "PIKED UP"}:
                issues.append("Keep your hips level")
                severity = "incorrect"
        selected_indices = (shoulder_idx, elbow_idx, wrist_idx, hip_idx, ankle_idx)
        return self.add_feedback(
            result,
            movement_valid=key_landmarks_visible,
            feedback_valid=key_landmarks_visible,
            confidence_values=[landmarks[index].visibility for index in selected_indices],
            previous_reps=previous_reps,
            issues=issues,
            severity=severity,
        )
    

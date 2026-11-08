from core.base_excercise import BaseExcercise

class SquatDetector(BaseExcercise):
    DOWN_THRESHOLD = 100   
    UP_THRESHOLD = 160     
    MIN_VISIBILITY = 0.7

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

    def reset(self):
        self.reset_rep_tracking()

    def process(self,landmarks):
        previous_reps = self.reps
        #find angle of both leg the leg with more visiblities are considered
        
        left_knee_angle = self.calculate_angle(
            self.get_point(landmarks, self.LEFT_HIP),
            self.get_point(landmarks, self.LEFT_KNEE),
            self.get_point(landmarks, self.LEFT_ANKLE)
        )

        right_knee_angle = self.calculate_angle(
            self.get_point(landmarks, self.RIGHT_HIP),
            self.get_point(landmarks, self.RIGHT_KNEE),
            self.get_point(landmarks, self.RIGHT_ANKLE)
        )

        left_visible = all(landmarks[index].visibility > self.MIN_VISIBILITY for index in (self.LEFT_HIP, self.LEFT_KNEE, self.LEFT_ANKLE))
        right_visible = all(landmarks[index].visibility > self.MIN_VISIBILITY for index in (self.RIGHT_HIP, self.RIGHT_KNEE, self.RIGHT_ANKLE))
        left_score = min(landmarks[index].visibility for index in (self.LEFT_HIP, self.LEFT_KNEE, self.LEFT_ANKLE))
        right_score = min(landmarks[index].visibility for index in (self.RIGHT_HIP, self.RIGHT_KNEE, self.RIGHT_ANKLE))

        if left_visible and right_visible:
            use_left = left_score >= right_score
        elif left_visible:
            use_left = True
        elif right_visible:
            use_left = False
        else:
            use_left = left_score >= right_score

        if use_left:
            knee_angle = left_knee_angle
            hip_idx, knee_idx, ankle_idx, shoulder_idx = self.LEFT_HIP, self.LEFT_KNEE, self.LEFT_ANKLE, self.LEFT_SHOULDER
        else:
            knee_angle = right_knee_angle
            hip_idx, knee_idx, ankle_idx, shoulder_idx = self.RIGHT_HIP, self.RIGHT_KNEE, self.RIGHT_ANKLE, self.RIGHT_SHOULDER
        key_landmark_visible = left_visible if use_left else right_visible
        back_angle = (
            int(self.calculate_angle(
                self.get_point(landmarks, shoulder_idx),
                self.get_point(landmarks, hip_idx),
                self.get_point(landmarks, knee_idx),
            ))
            if key_landmark_visible and landmarks[shoulder_idx].visibility > self.MIN_VISIBILITY
            else "N/A"
        )

        if key_landmark_visible:
            self.update_rep_stage(
                knee_angle,
                low_threshold=self.DOWN_THRESHOLD,
                high_threshold=self.UP_THRESHOLD,
                low_stage="down",
                high_stage="up",
                count_stage="up",
            )

        if not key_landmark_visible:
            depth_status = "N/A"
        elif self.stage == "down":
            depth_status = "GOOD DEPTH" if knee_angle <= self.DOWN_THRESHOLD else "TOO HIGH"
        elif self.stage == "up":
            depth_status = "STANDING"
        else:
            depth_status = "N/A"
        result = {
            "reps": self.reps,
            "knee_angle": int(knee_angle) if key_landmark_visible else "N/A",
            "back_angle": back_angle,
            "depth_status": depth_status,
            "landmarks_visible": key_landmark_visible,
        }
        issues = []
        if key_landmark_visible:
            if depth_status == "TOO HIGH":
                issues.append("Increase squat depth")
            if isinstance(back_angle, int) and back_angle < 130:
                issues.append("Keep your torso more upright")
        selected_indices = (hip_idx, knee_idx, ankle_idx)
        return self.add_feedback(
            result,
            movement_valid=key_landmark_visible,
            feedback_valid=key_landmark_visible and back_angle != "N/A",
            confidence_values=[landmarks[index].visibility for index in selected_indices],
            previous_reps=previous_reps,
            issues=issues,
        )

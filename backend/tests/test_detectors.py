import sys
import math
import unittest
from pathlib import Path
from types import SimpleNamespace

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from detectors.biceps_curl import BicepsCurlDetector  # noqa: E402
from detectors.lunges import LungesDetector  # noqa: E402
from detectors.pushup import PushUpDetector  # noqa: E402
from detectors.shoulder_press import ShoulderPressDetector  # noqa: E402
from detectors.squat import SquatDetector  # noqa: E402


DETECTOR_CASES = (
    ("squat", SquatDetector, (23, 25, 27), (90, 170)),
    ("push-up", PushUpDetector, (11, 13, 15), (80, 170)),
    ("curl", BicepsCurlDetector, (11, 13, 15), (40, 170)),
    ("shoulder press", ShoulderPressDetector, (11, 13, 15), (80, 170)),
    ("lunge", LungesDetector, (23, 25, 27), (90, 170)),
)
FEEDBACK_CASES = (
    ("squat", SquatDetector, ((23, 25, 27), (24, 26, 28)), ("depth_status", "back_angle")),
    ("push-up", PushUpDetector, ((11, 13, 15), (12, 14, 16)), ("body_alignment", "hip_status")),
    ("curl", BicepsCurlDetector, ((11, 13, 15), (12, 14, 16)), ("shoulder_status", "swing_status")),
    ("shoulder press", ShoulderPressDetector, ((11, 13, 15), (12, 14, 16)), ("extension_status", "back_arch_status")),
    ("lunge", LungesDetector, ((23, 25, 27), (24, 26, 28)), ("torso_angle", "balance_status")),
)


def landmarks():
    return [SimpleNamespace(x=0.2 + (index % 8) * 0.01, y=0.5, visibility=1.0) for index in range(33)]


def set_joint_angle(points, indices, degrees, visibility=1.0):
    first, joint, last = indices
    theta = degrees * 3.141592653589793 / 180
    points[joint].x, points[joint].y = 0.5, 0.5
    points[first].x, points[first].y = 0.5, 0.4
    points[last].x = 0.5 + 0.1 * math.sin(theta)
    points[last].y = 0.5 - 0.1 * math.cos(theta)
    for index in indices:
        points[index].visibility = visibility


class DetectorMovementTests(unittest.TestCase):
    def test_each_detector_counts_one_complete_movement_cycle(self) -> None:
        for name, detector_type, indices, (down_angle, up_angle) in DETECTOR_CASES:
            with self.subTest(exercise=name):
                detector = detector_type()
                points = landmarks()
                cycle = (down_angle, up_angle, down_angle) if name == "shoulder press" else (up_angle, down_angle, up_angle)
                rep_completed = False
                for angle in cycle:
                    set_joint_angle(points, indices, angle)
                    for _ in range(detector.REP_STAGE_CONFIRM_FRAMES):
                        result = detector.process(points)
                        rep_completed = rep_completed or result["rep_completed"]
                self.assertEqual(result["reps"], 1)
                self.assertTrue(rep_completed)
                self.assertTrue(result["movement_valid"])
                self.assertGreater(result["pose_confidence"], 0.7)
                self.assertIn(result["form_status"], {"good", "warning", "incorrect"})
                self.assertIn(result["feedback_priority"], {"positive", "medium", "high"})
                set_joint_angle(points, indices, up_angle)
                self.assertFalse(detector.process(points)["rep_completed"])

    def test_no_detector_counts_a_partial_movement(self) -> None:
        for name, detector_type, indices, (down_angle, _) in DETECTOR_CASES:
            with self.subTest(exercise=name):
                detector = detector_type()
                points = landmarks()
                set_joint_angle(points, indices, down_angle)
                result = detector.process(points)
                self.assertEqual(result["reps"], 0)

    def test_no_detector_counts_when_required_joints_are_not_visible(self) -> None:
        for name, detector_type, indices, (down_angle, up_angle) in DETECTOR_CASES:
            with self.subTest(exercise=name):
                detector = detector_type()
                points = landmarks()
                set_joint_angle(points, indices, down_angle, visibility=0.1)
                detector.process(points)
                set_joint_angle(points, indices, up_angle, visibility=0.1)
                result = detector.process(points)
                self.assertEqual(result["reps"], 0)

    def test_hidden_landmarks_do_not_produce_form_feedback(self) -> None:
        for name, detector_type, side_indices, feedback_keys in FEEDBACK_CASES:
            with self.subTest(exercise=name):
                detector = detector_type()
                points = landmarks()
                for indices in side_indices:
                    set_joint_angle(points, indices, 90, visibility=0.1)
                result = detector.process(points)
                for key in feedback_keys:
                    self.assertEqual(result[key], "N/A", f"{key} should wait for visible landmarks")
                self.assertFalse(result["movement_valid"])
                self.assertEqual(result["form_status"], "waiting")
                self.assertEqual(result["feedback_priority"], "waiting")
                self.assertEqual(result["form_issue"], "")

    def test_lunge_counts_using_visible_right_leg_when_left_leg_is_hidden(self) -> None:
        detector = LungesDetector()
        points = landmarks()
        set_joint_angle(points, (23, 25, 27), 170, visibility=0.1)
        set_joint_angle(points, (24, 26, 28), 170)
        points[12].visibility = 1.0

        detector.process(points)
        set_joint_angle(points, (24, 26, 28), 90)
        detector.process(points)
        detector.process(points)
        set_joint_angle(points, (24, 26, 28), 170)
        detector.process(points)
        result = detector.process(points)

        self.assertEqual(result["reps"], 1)

    def test_arm_detectors_use_a_visible_side_when_the_other_side_is_partial(self) -> None:
        cases = (
            ("push-up", PushUpDetector, (12, 14, 16), (80, 170), (11, 13, 15)),
            ("curl", BicepsCurlDetector, (12, 14, 16), (40, 170), (11, 13, 15)),
            ("shoulder press", ShoulderPressDetector, (12, 14, 16), (80, 170), (11, 13, 15)),
        )
        for name, detector_type, visible_arm, angles, partial_arm in cases:
            with self.subTest(exercise=name):
                detector = detector_type()
                points = landmarks()
                left_shoulder, left_elbow, left_wrist = partial_arm
                points[left_shoulder].visibility = 0.1
                points[left_elbow].visibility = 0.9
                points[left_wrist].visibility = 0.1
                if name == "push-up":
                    points[23].visibility = 0.1
                    points[27].visibility = 0.1

                for angle in (angles[1], angles[0], angles[1]):
                    set_joint_angle(points, visible_arm, angle)
                    points[visible_arm[1]].visibility = 0.8
                    for _ in range(detector.REP_STAGE_CONFIRM_FRAMES):
                        result = detector.process(points)
                self.assertEqual(result["reps"], 1)

    def test_reset_clears_detector_rep_and_movement_state(self) -> None:
        for name, detector_type, indices, (down_angle, up_angle) in DETECTOR_CASES:
            with self.subTest(exercise=name):
                detector = detector_type()
                points = landmarks()
                cycle = (down_angle, up_angle, down_angle) if name == "shoulder press" else (up_angle, down_angle, up_angle)
                for angle in cycle:
                    set_joint_angle(points, indices, angle)
                    for _ in range(detector.REP_STAGE_CONFIRM_FRAMES):
                        detector.process(points)
                detector.reset()
                self.assertEqual(detector.reps, 0)
                self.assertIsNone(detector.stage)

    def test_curl_swing_angle_handles_horizontal_torso_vector(self) -> None:
        detector = BicepsCurlDetector()
        self.assertEqual(detector._safe_angle(1.0, 0.0), 90.0)

    def test_curl_returns_a_structured_warning_for_visible_torso_swing(self) -> None:
        detector = BicepsCurlDetector()
        points = landmarks()
        set_joint_angle(points, (11, 13, 15), 40)
        detector.process(points)
        detector.process(points)
        points[11].x = points[12].x = 0.7
        points[11].y = points[12].y = 0.3
        points[23].x = points[24].x = 0.4
        points[23].y = points[24].y = 0.6

        result = detector.process(points)

        self.assertEqual(result["form_status"], "warning")
        self.assertEqual(result["feedback_priority"], "medium")
        self.assertIn("Avoid swinging your torso", result["form_issue"])
        self.assertEqual(result["exercise_stage"], "up")

    def test_single_frame_threshold_jitter_does_not_complete_a_rep(self) -> None:
        for name, detector_type, indices, (down_angle, up_angle) in DETECTOR_CASES:
            with self.subTest(exercise=name):
                detector = detector_type()
                points = landmarks()
                cycle = (down_angle, up_angle, down_angle) if name == "shoulder press" else (up_angle, down_angle, up_angle)
                for angle in cycle[:2]:
                    set_joint_angle(points, indices, angle)
                    for _ in range(detector.REP_STAGE_CONFIRM_FRAMES):
                        detector.process(points)
                set_joint_angle(points, indices, cycle[2])
                detector.process(points)
                set_joint_angle(points, indices, 130)
                result = detector.process(points)
                self.assertEqual(result["reps"], 0)


if __name__ == "__main__":
    unittest.main()

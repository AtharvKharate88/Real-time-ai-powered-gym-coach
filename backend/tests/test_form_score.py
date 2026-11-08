import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from services.vision.form_score import FormScoreAccumulator  # noqa: E402


class FormScoreAccumulatorTests(unittest.TestCase):
    def test_default_score_requires_thirty_valid_frames(self) -> None:
        score = FormScoreAccumulator()
        for _ in range(29):
            score.record({"movement_valid": True, "form_status": "good"})
        self.assertIsNone(score.get_score())
        score.record({"movement_valid": True, "form_status": "good"})
        self.assertEqual(score.get_score(), 100)

    def test_score_is_unavailable_without_enough_valid_observations(self) -> None:
        score = FormScoreAccumulator(min_samples=3)
        self.assertIsNone(score.get_score())
        score.record({"movement_valid": True, "form_status": "good"})
        score.record({"movement_valid": False, "form_status": "good"})
        self.assertIsNone(score.get_score())

    def test_score_averages_detector_statuses_only_for_valid_observations(self) -> None:
        score = FormScoreAccumulator(min_samples=3)
        score.record({"movement_valid": True, "form_status": "good"})
        score.record({"movement_valid": True, "form_status": "warning"})
        score.record({"movement_valid": True, "form_status": "incorrect"})
        score.record({"movement_valid": False, "form_status": "good"})
        self.assertEqual(score.get_score(), 75)

    def test_unknown_or_waiting_statuses_do_not_count_as_good_form(self) -> None:
        score = FormScoreAccumulator(min_samples=1)
        score.record({"movement_valid": True, "form_status": "waiting"})
        score.record({"movement_valid": True, "form_status": "unrecognized"})
        self.assertIsNone(score.get_score())


if __name__ == "__main__":
    unittest.main()

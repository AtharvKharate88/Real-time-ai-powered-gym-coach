import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from database.repositories.exercise_repository import add_exercise  # noqa: E402


class ExerciseRepositoryTests(unittest.TestCase):
    def test_each_finished_session_is_inserted_with_its_form_score(self) -> None:
        db = Mock()
        session_factory = MagicMock()
        session_factory.begin.return_value.__enter__.return_value = db

        with patch("database.repositories.exercise_repository.SessionLocal", session_factory):
            add_exercise(11, "Squats", 18, 2, 62, form_score=82)

        saved = db.add.call_args.args[0]
        self.assertEqual(saved.user_id, 11)
        self.assertEqual(saved.exercise_name, "Squats")
        self.assertEqual(saved.form_score, 82)
        db.scalar.assert_not_called()

    def test_missing_form_score_remains_null_for_unscored_workouts(self) -> None:
        db = Mock()
        session_factory = MagicMock()
        session_factory.begin.return_value.__enter__.return_value = db

        with patch("database.repositories.exercise_repository.SessionLocal", session_factory):
            add_exercise(11, "Lunges", 0, 0, 10)

        self.assertIsNone(db.add.call_args.args[0].form_score)


if __name__ == "__main__":
    unittest.main()

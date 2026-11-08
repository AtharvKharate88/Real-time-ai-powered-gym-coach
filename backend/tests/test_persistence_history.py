import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env", override=True)

from api.services.persistence import get_history  # noqa: E402


class HistorySerializationTests(unittest.TestCase):
    def test_authenticated_history_serializes_timestamps_as_iso_strings(self) -> None:
        created_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        entry = {
            "id": 12,
            "user_id": 7,
            "exercise_name": "Squats",
            "reps": 10,
            "sets": 1,
            "time": 33.5,
            "created_at": created_at,
        }
        with patch(
            "api.services.persistence.get_users_exercises", return_value=[entry]
        ):
            history = get_history(7)
        self.assertEqual(history[0]["created_at"], created_at.isoformat())


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env", override=True)

from fastapi import HTTPException  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from api.main import app  # noqa: E402
from api.routes import workouts  # noqa: E402
from api.routes import health  # noqa: E402
from api.services.workout_access import get_request_session  # noqa: E402
from api.services.workout_sessions import WorkoutSession  # noqa: E402
from api.services.workout_sessions import session_manager  # noqa: E402


class WorkoutOwnershipTests(unittest.TestCase):
    def test_anonymous_users_cannot_create_workout_sessions(self) -> None:
        response = TestClient(app).post(
            "/api/workouts/sessions",
            json={"exercise": "Squats", "target_sets": 3, "reps_per_set": 10},
        )
        if response.status_code == 201:
            session_manager.remove(response.json()["session_id"])
        self.assertEqual(response.status_code, 401)

    def test_session_is_hidden_from_a_different_user(self) -> None:
        session = WorkoutSession("Squats", 3, 10, user_id=7)
        request = SimpleNamespace()
        with (
            patch("api.services.workout_access.session_manager.get", return_value=session),
            patch(
                "api.services.workout_access.optional_current_user",
                return_value=SimpleNamespace(id=8),
            ),
        ):
            with self.assertRaises(HTTPException) as raised:
                get_request_session("session-id", request)
        self.assertEqual(raised.exception.status_code, 404)

    def test_session_is_available_to_its_owner(self) -> None:
        session = WorkoutSession("Squats", 3, 10, user_id=7)
        request = SimpleNamespace()
        with (
            patch("api.services.workout_access.session_manager.get", return_value=session),
            patch(
                "api.services.workout_access.optional_current_user",
                return_value=SimpleNamespace(id=7),
            ),
        ):
            self.assertIs(get_request_session("session-id", request), session)

    def test_history_queries_only_the_signed_in_users_records(self) -> None:
        request = SimpleNamespace()
        with (
            patch(
                "api.routes.workouts.optional_current_user",
                return_value=SimpleNamespace(id=7),
            ),
            patch("api.routes.workouts.get_history", return_value=[]) as get_history,
        ):
            workouts.history(request)
        get_history.assert_called_once_with(7)

    def test_completed_session_exposes_and_persists_its_estimated_form_score(self) -> None:
        class ScoredProcessor:
            def get_latest_metrics(self):
                return {
                    "reps": 10,
                    "pose_detected": True,
                    "movement_valid": True,
                    "form_status": "warning",
                }

            def get_form_score(self):
                return 82

        session = WorkoutSession("Squats", 1, 10, user_id=7)
        session.processor = ScoredProcessor()
        session.start()
        session.queue_voice_event = lambda *_args, **_kwargs: None
        with (
            patch("api.routes.workouts.get_request_session", return_value=session),
            patch("api.routes.workouts.add_exercise") as persist,
        ):
            response = workouts.get_metrics("session-id", SimpleNamespace())

        self.assertEqual(response.form_score, 82)
        self.assertTrue(session.persisted)
        self.assertEqual(persist.call_args.args[:4], (7, "Squats", 10, 1))
        self.assertEqual(persist.call_args.args[5], 82)

    def test_voice_status_reports_when_coaching_is_not_configured(self) -> None:
        session = WorkoutSession("Squats", 3, 10, user_id=7)
        request = SimpleNamespace()
        with patch("api.routes.workouts.get_request_session", return_value=session):
            response = workouts.get_voice("session-id", request)
        self.assertFalse(response.available)
        self.assertIsNone(response.text)

    def test_voice_status_reports_when_a_coaching_cue_is_ready(self) -> None:
        pipeline = SimpleNamespace(get_result=lambda: (b"audio", "Keep your back straight."), get_error=lambda: None)
        session = WorkoutSession("Squats", 3, 10, user_id=7)
        session.voice_pipeline = pipeline
        request = SimpleNamespace()
        with patch("api.routes.workouts.get_request_session", return_value=session):
            response = workouts.get_voice("session-id", request)
        self.assertTrue(response.available)
        self.assertEqual(response.text, "Keep your back straight.")

    def test_voice_status_does_not_expose_internal_error_details(self) -> None:
        pipeline = SimpleNamespace(get_result=lambda: None, get_error=lambda: "private provider details")
        session = WorkoutSession("Squats", 3, 10, user_id=7)
        session.voice_pipeline = pipeline
        request = SimpleNamespace()
        with patch("api.routes.workouts.get_request_session", return_value=session):
            response = workouts.get_voice("session-id", request)
        self.assertTrue(response.error)
        self.assertIsNone(response.text)

    def test_database_health_does_not_return_connection_details(self) -> None:
        with patch(
            "api.routes.health.check_database_connection",
            return_value={"connected": True},
        ):
            self.assertEqual(
                health.database_health_check(),
                {"status": "ok", "message": "Database connection is healthy"},
            )

    def test_database_health_returns_503_on_connection_failure(self) -> None:
        with patch(
            "api.routes.health.check_database_connection",
            side_effect=RuntimeError("contains secret connection details"),
        ):
            with self.assertRaises(HTTPException) as raised:
                health.database_health_check()
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail, "Database unavailable")

    def test_workout_api_keeps_sessions_private_to_their_creator(self) -> None:
        def fake_user(request):
            user_id = request.headers.get("x-test-user")
            return SimpleNamespace(id=int(user_id)) if user_id else None

        with (
            patch("api.routes.workouts.current_user", side_effect=fake_user),
            patch("api.services.workout_access.optional_current_user", side_effect=fake_user),
        ):
            client = TestClient(app)
            created = client.post(
                "/api/workouts/sessions",
                headers={"x-test-user": "7"},
                json={"exercise": "Squats", "target_sets": 3, "reps_per_set": 10},
            )
            self.assertEqual(created.status_code, 201)
            session_id = created.json()["session_id"]
            try:
                owner_response = client.post(
                    f"/api/workouts/sessions/{session_id}/pause",
                    headers={"x-test-user": "7"},
                )
                other_user_response = client.post(
                    f"/api/workouts/sessions/{session_id}/pause",
                    headers={"x-test-user": "8"},
                )
            finally:
                session_manager.remove(session_id)

        self.assertEqual(owner_response.status_code, 200)
        self.assertEqual(other_user_response.status_code, 404)


if __name__ == "__main__":
    unittest.main()

"""Opt-in integration check against the configured Neon database."""

import os
import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env", override=True)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete, select  # noqa: E402

from api.config import settings  # noqa: E402
from api.main import app  # noqa: E402
from api.services.auth import create_session_token, upsert_google_user  # noqa: E402
from api.services.workout_sessions import session_manager  # noqa: E402
from database.engine import engine  # noqa: E402
from database.session import SessionLocal  # noqa: E402
from models import Exercise, User  # noqa: E402


@unittest.skipUnless(
    os.getenv("AI_GYM_NEON_TESTS") == "1",
    "set AI_GYM_NEON_TESTS=1 to run tests against Neon",
)
class NeonWorkoutIntegrationTests(unittest.TestCase):
    def test_completed_workout_is_persisted_and_isolated(self) -> None:
        suffix = uuid.uuid4().hex
        user_ids: list[int] = []
        session_id: str | None = None

        try:
            claims = [
                {
                    "sub": f"codex_verify_{suffix}_{index}",
                    "email": f"codex_verify_{suffix}_{index}@example.invalid",
                    "email_verified": True,
                    "name": f"Verification User {index}",
                    "picture": None,
                }
                for index in (1, 2)
            ]
            users = []
            for identity in claims:
                user = upsert_google_user(identity)
                user_ids.append(user.id)
                users.append(user)
            self.assertEqual(upsert_google_user(claims[0]).id, user_ids[0])
            tokens = [create_session_token(user) for user in users]

            class FakeProcessor:
                def get_latest_metrics(self) -> dict[str, int | bool]:
                    return {"reps": 10, "pose_detected": True}

                def get_form_score(self) -> int:
                    return 84

            owner = TestClient(app)
            owner.cookies.set(settings.auth_cookie_name, tokens[0])
            database_health = owner.get("/api/health/database")
            self.assertEqual(database_health.status_code, 200)
            self.assertEqual(owner.get("/api/auth/me").status_code, 200)
            created = owner.post(
                "/api/workouts/sessions",
                json={
                    "exercise": "Squats",
                    "target_sets": 1,
                    "reps_per_set": 10,
                },
            )
            self.assertEqual(created.status_code, 201)
            session_id = created.json()["session_id"]
            session = session_manager.get(session_id)
            assert session is not None
            session.processor = FakeProcessor()
            session.queue_voice_event = lambda *_args, **_kwargs: None

            self.assertEqual(
                owner.post(f"/api/workouts/sessions/{session_id}/start").status_code,
                200,
            )
            completion = owner.get(f"/api/workouts/sessions/{session_id}/metrics")
            self.assertEqual(completion.status_code, 200)
            self.assertTrue(completion.json()["workout_completed"])
            self.assertEqual(completion.json()["form_score"], 84)

            manual_time = datetime(2026, 10, 31, 12, tzinfo=timezone.utc)
            manual = owner.post(
                "/api/workouts/history/manual",
                json={
                    "exercise_name": "Lunges",
                    "reps": 18,
                    "sets": 3,
                    "time": 540,
                    "created_at": manual_time.isoformat(),
                },
            )
            self.assertEqual(manual.status_code, 201)
            self.assertEqual(manual.json()["created_at"], manual_time.isoformat())

            history = owner.get("/api/workouts/history")
            self.assertEqual(history.status_code, 200)
            self.assertEqual(len(history.json()), 2)
            tracked_entry = next(item for item in history.json() if item["exercise_name"] == "Squats")
            self.assertEqual(tracked_entry["reps"], 10)
            self.assertEqual(tracked_entry["form_score"], 84)
            self.assertEqual(tracked_entry["set_breakdown"], [10])
            self.assertIsInstance(history.json()[0]["created_at"], str)

            with SessionLocal() as db:
                persisted = db.scalar(
                    select(Exercise).where(Exercise.user_id == user_ids[0])
                )
                self.assertIsNotNone(persisted)
                self.assertEqual(persisted.reps, 10)
                self.assertEqual(persisted.form_score, 84)
                self.assertEqual(persisted.set_breakdown, [10])

            other_user = TestClient(app)
            other_user.cookies.set(settings.auth_cookie_name, tokens[1])
            self.assertEqual(other_user.get("/api/workouts/history").json(), [])
            self.assertEqual(
                other_user.get(
                    f"/api/workouts/sessions/{session_id}/metrics"
                ).status_code,
                404,
            )
        finally:
            if session_id:
                session_manager.remove(session_id)
            with SessionLocal.begin() as db:
                synthetic_user_ids = select(User.id).where(
                    User.email.like(f"codex_verify_{suffix}_%@example.invalid")
                )
                db.execute(
                    delete(Exercise).where(Exercise.user_id.in_(synthetic_user_ids))
                )
                db.execute(delete(User).where(User.id.in_(synthetic_user_ids)))
            engine.dispose()


if __name__ == "__main__":
    unittest.main()

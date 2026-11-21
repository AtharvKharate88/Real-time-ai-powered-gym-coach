import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from api.routes.workouts import finish_local_squats
from api.schemas.workout import LocalSquatSummary
from database.base import Base
from models import Exercise


class LocalWorkoutTests(unittest.TestCase):
    def test_retries_keep_one_immutable_owned_row(self):
        engine = create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        sessions = sessionmaker(engine)
        body = LocalSquatSummary(reps=12, reps_per_set=5, target_sets=3, elapsed_seconds=85,
                                 good_frames=30, warning_frames=20)
        identifier = uuid4()
        with patch("database.repositories.exercise_repository.SessionLocal", sessions), patch(
            "api.routes.workouts.current_user", return_value=SimpleNamespace(id=7)
        ) as user:
            for _ in range(2):
                self.assertEqual(finish_local_squats(identifier, body, object()), {"saved": True})
            with self.assertRaises(HTTPException) as conflict:
                finish_local_squats(identifier, body.model_copy(update={"reps": 11}), object())
            self.assertEqual(conflict.exception.status_code, 409)
            user.return_value = SimpleNamespace(id=8)
            finish_local_squats(identifier, body, object())
        with sessions() as db:
            rows = db.scalars(select(Exercise).order_by(Exercise.user_id)).all()
            self.assertEqual([row.user_id for row in rows], [7, 8])
            self.assertEqual((rows[0].reps, rows[0].sets, rows[0].set_breakdown, rows[0].form_score),
                             (12, 2, [5, 5, 2], 90))

    def test_rejects_untrusted_summary_fields_and_out_of_range_counts(self):
        base = dict(reps=1, reps_per_set=1, target_sets=1, elapsed_seconds=3, good_frames=1, warning_frames=0)
        for change in ({"user_id": 7}, {"form_score": 101}, {"reps": 2}, {"warning_frames": -1}, {"reps": True}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                LocalSquatSummary(**(base | change))

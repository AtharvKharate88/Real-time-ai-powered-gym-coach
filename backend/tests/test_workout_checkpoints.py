import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.routes import local_workouts as routes
from api.schemas.workout import LocalProgress
from database.base import Base
from database.repositories import exercise_repository as history


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        engine=create_engine("sqlite://")
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        sessions=sessionmaker(engine)
        self.enterContext(patch.object(routes,"SessionLocal",sessions))
        self.enterContext(patch.object(history,"SessionLocal",sessions))
        self.enterContext(patch.object(routes,"current_user",return_value=SimpleNamespace(id=3)))
        self.wid=uuid4()
        self.p=LocalProgress(exercise="Shoulder Press",reps=2,reps_per_set=4,target_sets=3,
            elapsed_seconds=18,good_frames=10,warning_frames=10,incorrect_frames=10,revision=1,finished=False)

    def put(self, **changes):
        return routes.checkpoint(3,self.wid,self.p.model_copy(update=changes),None)

    def test_restore_retry_and_history(self):
        self.put()
        self.put()
        self.assertEqual(routes.drafts(3,None)[0]["progress"],self.p.model_dump())
        self.assertEqual(history.get_users_exercises(3),[])
        self.put(revision=6,reps=5,finished=True)
        self.put(revision=6,reps=5,finished=True)
        self.assertTrue(routes.saved_state(3,self.wid,None)["finished"])
        self.assertEqual(routes.drafts(3,None),[])
        rows=history.get_users_exercises(3)
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]["set_breakdown"],rows[0]["form_score"]),([4,1],75))
        with self.assertRaises(HTTPException): self.put(revision=7,reps=6)

    def test_cannot_rewind_or_change_exercise(self):
        self.put(revision=4)
        for change in [dict(revision=2),dict(revision=5,reps=1),dict(revision=5,exercise="Squats"),
                       dict(revision=5,warning_frames=9),dict(revision=5,target_sets=2)]:
            with self.subTest(change=change), self.assertRaises(HTTPException) as rejected:
                self.put(**change)
            self.assertEqual(rejected.exception.status_code,409)

    def test_empty_finish_and_account_change(self):
        self.put(reps=0,finished=True)
        self.assertEqual(routes.drafts(3,None),[])
        self.assertEqual(history.get_users_exercises(3),[])
        with self.assertRaises(HTTPException) as denied:
            routes.checkpoint(4,self.wid,self.p,None)
        self.assertEqual(denied.exception.status_code,403)


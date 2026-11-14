import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from services.coaching import voice_pipeline  # noqa: E402
from services.coaching.voice_pipeline import VoicePipeline  # noqa: E402


class VoicePipelineRateLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        voice_pipeline._GROQ_NEXT_REQUEST_AT = 0.0

    def make_pipeline(self, interval: float = 8.0) -> VoicePipeline:
        pipeline = VoicePipeline.__new__(VoicePipeline)
        pipeline._min_groq_interval_seconds = interval
        pipeline._last_groq_request_at = None
        pipeline._stop_event = Mock()
        pipeline._stop_event.is_set.return_value = False
        pipeline._stop_event.wait.return_value = False
        return pipeline

    def test_first_groq_request_does_not_wait(self) -> None:
        pipeline = self.make_pipeline()
        with patch(
            "services.coaching.voice_pipeline.time.monotonic",
            return_value=10.0,
        ):
            self.assertTrue(pipeline._wait_for_groq_rate_limit())

        pipeline._stop_event.wait.assert_not_called()
        self.assertEqual(voice_pipeline._GROQ_NEXT_REQUEST_AT, 18.0)

    def test_next_groq_request_waits_for_configured_minimum_interval(self) -> None:
        pipeline = self.make_pipeline(interval=8.0)
        voice_pipeline._GROQ_NEXT_REQUEST_AT = 18.0
        with patch(
            "services.coaching.voice_pipeline.time.monotonic",
            return_value=13.0,
        ):
            self.assertTrue(pipeline._wait_for_groq_rate_limit())

        pipeline._stop_event.wait.assert_called_once_with(5.0)
        self.assertEqual(voice_pipeline._GROQ_NEXT_REQUEST_AT, 26.0)

    def test_rate_limit_wait_can_be_cancelled(self) -> None:
        pipeline = self.make_pipeline()
        voice_pipeline._GROQ_NEXT_REQUEST_AT = 18.0
        pipeline._stop_event.wait.return_value = True
        with patch("services.coaching.voice_pipeline.time.monotonic", return_value=11.0):
            self.assertFalse(pipeline._wait_for_groq_rate_limit())

        pipeline._stop_event.wait.assert_called_once_with(7.0)
        self.assertEqual(voice_pipeline._GROQ_NEXT_REQUEST_AT, 26.0)


if __name__ == "__main__":
    unittest.main()

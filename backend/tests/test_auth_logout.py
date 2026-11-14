import sys
import unittest
from http.cookies import SimpleCookie
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env", override=True)

from api.config import settings  # noqa: E402
from api.routes.auth import google_callback, logout  # noqa: E402


class LogoutCookieTests(unittest.TestCase):
    def test_logout_expires_the_http_only_session_cookie(self) -> None:
        response = logout()
        cookies = SimpleCookie()
        cookies.load(response.headers["set-cookie"])

        session_cookie = cookies[settings.auth_cookie_name]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(session_cookie.value, "")
        self.assertEqual(session_cookie["max-age"], "0")
        self.assertTrue(session_cookie["expires"])
        self.assertTrue(session_cookie["httponly"])
        self.assertEqual(session_cookie["path"], "/")
        self.assertEqual(session_cookie["samesite"].lower(), "lax")
        self.assertEqual(bool(session_cookie["secure"]), settings.cookie_secure)


class OAuthCallbackTests(unittest.TestCase):
    def test_google_callback_returns_authenticated_user_to_dashboard(self) -> None:
        user = SimpleNamespace(id=1, email="athlete@example.com")
        with (
            patch("api.routes.auth.validate_state"),
            patch("api.routes.auth.exchange_code", new_callable=AsyncMock, return_value={"id_token": "verified-token"}),
            patch("api.routes.auth.verify_id_token", new_callable=AsyncMock, return_value={"sub": "google-user"}),
            patch("api.routes.auth.upsert_google_user", return_value=user),
            patch("api.routes.auth.create_session_token", return_value="session-token"),
        ):
            callback = google_callback(code="oauth-code", state="valid-state")
            try:
                callback.send(None)
            except StopIteration as completed:
                response = completed.value
            else:
                self.fail("Mocked OAuth callback unexpectedly performed asynchronous I/O")

        self.assertEqual(response.headers["location"], settings.frontend_origin + "/?view=dashboard")
        self.assertIn(settings.auth_cookie_name, response.headers["set-cookie"])

    def test_google_callback_preserves_static_host_subpath(self) -> None:
        user = SimpleNamespace(id=2, email="athlete@example.com")
        frontend_settings = SimpleNamespace(
            frontend_origin="https://athlete.example.com",
            frontend_redirect_url="https://athlete.example.com/Real-time-ai-powered-gym-coach",
            auth_cookie_name="ai_gym_session",
            cookie_secure=True,
            auth_cookie_samesite="none",
        )
        with (
            patch("api.routes.auth.settings", frontend_settings),
            patch("api.routes.auth.validate_state"),
            patch("api.routes.auth.exchange_code", new_callable=AsyncMock, return_value={"id_token": "verified-token"}),
            patch("api.routes.auth.verify_id_token", new_callable=AsyncMock, return_value={"sub": "google-user"}),
            patch("api.routes.auth.upsert_google_user", return_value=user),
            patch("api.routes.auth.create_session_token", return_value="session-token"),
        ):
            callback = google_callback(code="oauth-code", state="valid-state")
            try:
                callback.send(None)
            except StopIteration as completed:
                response = completed.value
            else:
                self.fail("Mocked OAuth callback unexpectedly performed asynchronous I/O")

        self.assertEqual(
            response.headers["location"],
            "https://athlete.example.com/Real-time-ai-powered-gym-coach/?view=dashboard",
        )


if __name__ == "__main__":
    unittest.main()

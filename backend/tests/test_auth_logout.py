import sys
import unittest
from http.cookies import SimpleCookie
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

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


class OAuthCallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_google_callback_returns_authenticated_user_to_dashboard(self) -> None:
        user = SimpleNamespace(id=1, email="athlete@example.com")
        with (
            patch("api.routes.auth.validate_state"),
            patch("api.routes.auth.exchange_code", return_value={"id_token": "verified-token"}),
            patch("api.routes.auth.verify_id_token", return_value={"sub": "google-user"}),
            patch("api.routes.auth.upsert_google_user", return_value=user),
            patch("api.routes.auth.create_session_token", return_value="session-token"),
        ):
            response = await google_callback(code="oauth-code", state="valid-state")

        self.assertEqual(response.headers["location"], settings.frontend_origin + "/?view=dashboard")
        self.assertIn(settings.auth_cookie_name, response.headers["set-cookie"])


if __name__ == "__main__":
    unittest.main()

import sys
import unittest
from http.cookies import SimpleCookie
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env", override=True)

from api.config import settings  # noqa: E402
from api.routes.auth import logout  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()

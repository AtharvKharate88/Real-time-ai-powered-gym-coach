"""Configuration for the FastAPI application."""

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
    environment: str = os.getenv("ENVIRONMENT", "development")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv(
        "GOOGLE_REDIRECT_URI",
        "http://localhost:8000/api/auth/google/callback",
    )
    session_secret: str = os.getenv("SESSION_SECRET", "")
    auth_cookie_name: str = os.getenv("AUTH_COOKIE_NAME", "ai_gym_session")
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    auth_cookie_samesite: str = os.getenv("AUTH_COOKIE_SAMESITE", "lax").lower()

    def validate_production(self) -> None:
        """Fail fast when production would run with insecure or placeholder auth settings."""
        if self.environment.lower() not in {"production", "prod"}:
            return

        frontend = urlsplit(self.frontend_origin)
        callback = urlsplit(self.google_redirect_uri)
        if frontend.scheme != "https" or not frontend.netloc or frontend.path or frontend.query or frontend.fragment:
            raise RuntimeError("Production FRONTEND_ORIGIN must be an HTTPS origin without a path.")
        if callback.scheme != "https" or not callback.netloc or callback.path != "/api/auth/google/callback" or callback.query or callback.fragment:
            raise RuntimeError("Production GOOGLE_REDIRECT_URI must be the HTTPS /api/auth/google/callback URL.")
        if not self.cookie_secure:
            raise RuntimeError("COOKIE_SECURE=true is required in production.")
        if self.auth_cookie_samesite not in {"lax", "strict", "none"}:
            raise RuntimeError("AUTH_COOKIE_SAMESITE must be lax, strict, or none.")
        if self.auth_cookie_samesite == "none" and not self.cookie_secure:
            raise RuntimeError("COOKIE_SECURE=true is required when AUTH_COOKIE_SAMESITE=none.")
        if len(self.session_secret) < 32 or self.session_secret.lower().startswith(("replace", "your_")):
            raise RuntimeError("Production SESSION_SECRET must be a unique random value of at least 32 characters.")
        if not self.google_client_id or not self.google_client_secret or "your_" in self.google_client_id.lower() or "your_" in self.google_client_secret.lower():
            raise RuntimeError("Production Google OAuth client credentials are missing or still use placeholders.")


settings = Settings()

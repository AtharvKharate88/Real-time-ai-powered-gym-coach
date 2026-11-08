"""Configuration for the FastAPI application."""

import os
from dataclasses import dataclass

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


settings = Settings()

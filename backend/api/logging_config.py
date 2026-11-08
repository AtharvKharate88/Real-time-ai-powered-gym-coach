"""Logging setup for the FastAPI application."""

import logging

from .config import settings


def configure_logging() -> None:
    """Configure concise application logging once at startup."""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

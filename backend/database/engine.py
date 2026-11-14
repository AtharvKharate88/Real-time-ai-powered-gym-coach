
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import SQLAlchemyError

load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def get_database_url() -> str:
    """Return and validate the pooled Neon application URL."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is missing from backend/.env")

    url = make_url(database_url)

    if url.drivername != "postgresql+psycopg":
        raise RuntimeError(
            "DATABASE_URL must use postgresql+psycopg."
        )

    if "-pooler" not in (url.host or ""):
        raise RuntimeError(
            "DATABASE_URL must use Neon's pooled connection."
        )

    return database_url


DATABASE_URL = get_database_url()

engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    pool_timeout=30,
    pool_recycle=300,
    echo=False,
)


def check_database_connection() -> dict:
    """Verify connectivity without exposing credentials."""
    try:
        with engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT
                        current_database(),
                        current_user,
                        version()
                    """
                )
            )

            database, user, version = result.one()

            return {
                "connected": True,
                "database": database,
                "user": user,
                "version": version,
            }

    except SQLAlchemyError as exc:
        raise RuntimeError(
            "Unable to connect to Neon PostgreSQL."
        ) from exc


import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

# Locate the backend directory.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Load backend/.env.
load_dotenv(BACKEND_DIR / ".env")

from database.base import Base  # noqa: E402
import models  # noqa: E402,F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy models will register their tables here.
target_metadata = Base.metadata


def get_direct_database_url() -> str:
    """Get and validate Neon's direct connection URL."""

    database_url = os.getenv("DIRECT_DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DIRECT_DATABASE_URL is missing from backend/.env"
        )

    url = make_url(database_url)

    if url.drivername != "postgresql+psycopg":
        raise RuntimeError(
            "DIRECT_DATABASE_URL must use postgresql+psycopg."
        )

    if "-pooler" in (url.host or ""):
        raise RuntimeError(
            "Alembic requires Neon's direct connection, not the pooler."
        )

    return database_url


def run_migrations_offline() -> None:
    """Configure migrations without opening a connection."""

    context.configure(
        url=get_direct_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using Neon's direct connection."""

    connectable = create_engine(
        get_direct_database_url(),
        poolclass=NullPool,
        pool_pre_ping=True,
    )

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

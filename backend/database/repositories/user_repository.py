
"""User database operations using SQLAlchemy."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database.session import SessionLocal
from models import User


def get_user(username: str) -> dict | None:
    """Retrieve a user by username."""

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(User.username == username)
        )

        if user is None:
            return None

        return {
            "id": user.id,
            "username": user.username,
            "created_at": user.created_at,
        }


def create_user(username: str) -> dict:
    """Create a new user and return its data."""

    with SessionLocal() as db:
        user = User(username=username)

        try:
            db.add(user)
            db.commit()
            db.refresh(user)

            return {
                "id": user.id,
                "username": user.username,
                "created_at": user.created_at,
            }

        except IntegrityError:
            db.rollback()
            raise


def get_or_create_user(username: str) -> dict:
    """Retrieve an existing user or create one safely."""

    existing_user = get_user(username)

    if existing_user is not None:
        return existing_user

    try:
        return create_user(username)

    except IntegrityError:
        # Another request may have created the same username.
        existing_user = get_user(username)

        if existing_user is not None:
            return existing_user

        raise

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from database.engine import engine


SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    Provide a database session and close it after use.

    Intended for FastAPI dependency injection.
    """
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
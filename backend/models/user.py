
from datetime import datetime

from sqlalchemy import DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    username: Mapped[str] = mapped_column(
        Text,
        unique=True,
        nullable=False,
        index=True,
    )

    google_sub: Mapped[str | None] = mapped_column(
        Text,
        unique=True,
        nullable=True,
        index=True,
    )

    email: Mapped[str | None] = mapped_column(
        Text,
        unique=True,
        nullable=True,
        index=True,
    )

    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    picture_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username!r})>"

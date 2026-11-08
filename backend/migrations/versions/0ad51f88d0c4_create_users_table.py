
"""create users and exercises tables

Revision ID: 0ad51f88d0c4
Revises:
Create Date: 2026-11-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0ad51f88d0c4"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create users and exercises tables."""

    # Create users first because exercises references users.
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_users_username"),
        "users",
        ["username"],
        unique=True,
    )

    # Create exercises after users.
    op.create_table(
        "exercises",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("exercise_name", sa.Text(), nullable=False),
        sa.Column(
            "reps",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "sets",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "time",
            sa.Float(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f("ix_exercises_user_id"),
        "exercises",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove exercises and users tables."""

    # Drop dependent table first.
    op.drop_index(
        op.f("ix_exercises_user_id"),
        table_name="exercises",
    )
    op.drop_table("exercises")

    op.drop_index(
        op.f("ix_users_username"),
        table_name="users",
    )
    op.drop_table("users")

"""add Google identity fields to users

Revision ID: 1c8b1f6d5f31
Revises: 0ad51f88d0c4
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1c8b1f6d5f31"
down_revision: Union[str, Sequence[str], None] = "0ad51f88d0c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("google_sub", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("email", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("full_name", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("picture_url", sa.Text(), nullable=True))
    op.create_index("ix_users_google_sub", "users", ["google_sub"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_google_sub", table_name="users")
    op.drop_column("users", "picture_url")
    op.drop_column("users", "full_name")
    op.drop_column("users", "email")
    op.drop_column("users", "google_sub")

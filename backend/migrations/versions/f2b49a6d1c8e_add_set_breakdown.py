"""Persist per-set rep counts for workout history.

Revision ID: f2b49a6d1c8e
Revises: c41f8a7d2e60
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2b49a6d1c8e"
down_revision: Union[str, Sequence[str], None] = "c41f8a7d2e60"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exercises", sa.Column("set_breakdown", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("exercises", "set_breakdown")

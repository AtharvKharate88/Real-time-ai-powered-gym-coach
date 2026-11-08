"""Add nullable estimated form score to workout history.

Revision ID: c41f8a7d2e60
Revises: 1c8b1f6d5f31
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c41f8a7d2e60"
down_revision: Union[str, Sequence[str], None] = "1c8b1f6d5f31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exercises", sa.Column("form_score", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_exercises_form_score_range",
        "exercises",
        "form_score IS NULL OR (form_score >= 0 AND form_score <= 100)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_exercises_form_score_range", "exercises", type_="check")
    op.drop_column("exercises", "form_score")

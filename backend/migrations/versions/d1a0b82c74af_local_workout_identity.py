"""Identify retried local workout submissions within each account."""
import sqlalchemy as sa
from alembic import op

revision = "d1a0b82c74af"
down_revision = "f2b49a6d1c8e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("exercises", sa.Column("client_workout_id", sa.Text(), nullable=True))
    op.create_unique_constraint("uq_exercises_user_client_workout", "exercises", ["user_id", "client_workout_id"])


def downgrade() -> None:
    op.drop_constraint("uq_exercises_user_client_workout", "exercises", type_="unique")
    op.drop_column("exercises", "client_workout_id")

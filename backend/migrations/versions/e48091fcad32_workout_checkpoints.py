"""Store recoverable workout checkpoints separately from visible history."""
from alembic import op
import sqlalchemy as sa

revision = "e48091fcad32"
down_revision = "d1a0b82c74af"
branch_labels = depends_on = None

def upgrade():
    op.add_column("exercises", sa.Column("progress", sa.JSON(), nullable=True))
    op.add_column("exercises", sa.Column("progress_revision", sa.Integer(), nullable=True))

def downgrade():
    # Incomplete sessions must not become completed history in the previous schema.
    op.execute("DELETE FROM exercises WHERE progress_revision IS NOT NULL")
    op.drop_column("exercises", "progress_revision")
    op.drop_column("exercises", "progress")


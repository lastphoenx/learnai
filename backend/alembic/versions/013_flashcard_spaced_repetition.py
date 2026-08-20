"""Spaced repetition fields on flashcard_progress."""

from alembic import op
import sqlalchemy as sa

revision = "013_flashcard_spaced_repetition"
down_revision = "012_exam_trainer_unit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "flashcard_progress",
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "flashcard_progress",
        sa.Column("interval_days", sa.SmallInteger(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("flashcard_progress", "interval_days")
    op.drop_column("flashcard_progress", "next_review_at")

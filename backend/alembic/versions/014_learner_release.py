"""Freigabe von Lerneinheiten für Kinder (manuell oder auto bei guter Didaktik-Qualität)."""

from alembic import op
import sqlalchemy as sa

revision = "014_learner_release"
down_revision = "013_flashcard_spaced_repetition"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "learning_units",
        sa.Column("learner_released_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "learning_units",
        sa.Column("learner_release_mode", sa.String(length=16), nullable=True),
    )
    # Bestehende fertige Einheiten: Kinder behalten Zugriff (kein harter Cutover).
    op.execute(
        """
        UPDATE learning_units
        SET learner_released_at = COALESCE(updated_at, created_at),
            learner_release_mode = 'legacy'
        WHERE status = 'ready'
        """
    )


def downgrade() -> None:
    op.drop_column("learning_units", "learner_release_mode")
    op.drop_column("learning_units", "learner_released_at")

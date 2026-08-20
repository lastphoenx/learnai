"""Migration 011: Lernkarten-Fortschritt pro Profil."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, Sequence[str], None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "flashcard_progress",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("learning_record_id", sa.UUID(), nullable=False),
        sa.Column("unit_module_id", sa.UUID(), nullable=False),
        sa.Column("card_index", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="unseen"),
        sa.Column("attempts", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["learning_record_id"], ["learning_records.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["profile_id"], ["learning_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_module_id"], ["unit_modules.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_id",
            "unit_module_id",
            "card_index",
            name="uq_flashcard_progress_card",
        ),
    )
    op.create_index(
        "ix_flashcard_progress_profile_module",
        "flashcard_progress",
        ["profile_id", "unit_module_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_flashcard_progress_profile_module", table_name="flashcard_progress")
    op.drop_table("flashcard_progress")

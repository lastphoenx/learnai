"""Migration 008: Schulprüfungen (exam_results) — Phase A."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, Sequence[str], None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "exam_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column(
            "record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("learning_records.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("learning_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("learning_profiles.id"),
            nullable=True,
        ),
        sa.Column(
            "uploaded_by_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("taken_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exam_type", sa.String(length=32), nullable=False, server_default="klassenarbeit"),
        sa.Column("grade_label_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("score", sa.SmallInteger(), nullable=True),
        sa.Column("max_score", sa.SmallInteger(), nullable=True),
        sa.Column("notes_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("original_name_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("byte_size", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="uploaded"),
        sa.Column("classification", sa.SmallInteger(), nullable=False, server_default="2"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_exam_results_record", "exam_results", ["record_id"])
    op.create_index("ix_exam_results_unit", "exam_results", ["unit_id"])
    op.alter_column("exam_results", "exam_type", server_default=None)
    op.alter_column("exam_results", "byte_size", server_default=None)
    op.alter_column("exam_results", "status", server_default=None)
    op.alter_column("exam_results", "classification", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_exam_results_unit", table_name="exam_results")
    op.drop_index("ix_exam_results_record", table_name="exam_results")
    op.drop_table("exam_results")

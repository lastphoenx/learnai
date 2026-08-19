"""LearnAI – 2FA-Policy, Lerneinheiten, Verlauf

Revision ID: 004
Revises: 003
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("totp_required", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.alter_column("users", "totp_required", server_default=None)

    op.create_table(
        "learning_units",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("learner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("brief_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("subject", sa.String(length=64), nullable=True),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("target_age", sa.String(length=32), nullable=True),
        sa.Column("difficulty", sa.SmallInteger(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("auto_purge_sources", sa.Boolean(), nullable=False),
        sa.Column("classification", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["learner_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "unit_modules",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_index", sa.SmallInteger(), nullable=False),
        sa.Column("title_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("content_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("quiz_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["unit_id"], ["learning_units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "unit_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("original_name_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("byte_size", sa.BigInteger(), nullable=False),
        sa.Column("extracted_text_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("analysis_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("purged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["unit_id"], ["learning_units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "learning_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("summary_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("subject", sa.String(length=64), nullable=True),
        sa.Column("language", sa.String(length=8), nullable=False),
        sa.Column("difficulty", sa.SmallInteger(), nullable=False),
        sa.Column("reconstruction_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("stats_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("last_activity_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["unit_id"], ["learning_units.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_learning_records_user", "learning_records", ["tenant_id", "user_id"])

    op.create_table(
        "learning_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("record_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("payload_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["record_id"], ["learning_records.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("learning_events")
    op.drop_index("ix_learning_records_user", table_name="learning_records")
    op.drop_table("learning_records")
    op.drop_table("unit_sources")
    op.drop_table("unit_modules")
    op.drop_table("learning_units")
    op.drop_column("users", "totp_required")

"""Phase 3 – RBAC, Task-Status

Revision ID: 003
Revises: 002
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.SmallInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_project_members_project_user",
        "project_members",
        ["project_id", "user_id"],
        unique=True,
    )

    op.add_column(
        "tasks",
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
    )
    op.alter_column("tasks", "status", server_default=None)

    # Bestehende Projekte: Ersteller als Owner eintragen
    op.execute(
        sa.text(
            """
            INSERT INTO project_members (id, project_id, user_id, role, created_at, updated_at)
            SELECT gen_random_uuid(), p.id, p.created_by_id, 4, now(), now()
            FROM projects p
            WHERE NOT EXISTS (
                SELECT 1 FROM project_members pm
                WHERE pm.project_id = p.id AND pm.user_id = p.created_by_id
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_column("tasks", "status")
    op.drop_index("ix_project_members_project_user", table_name="project_members")
    op.drop_table("project_members")

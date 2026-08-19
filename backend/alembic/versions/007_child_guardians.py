"""Mehrere Eltern pro Kind (child_guardians).

Revision ID: 007
Revises: 006
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, Sequence[str], None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "child_guardians",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "parent_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "child_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_child_guardians_parent_child",
        "child_guardians",
        ["parent_user_id", "child_user_id"],
        unique=True,
    )
    op.create_index("ix_child_guardians_child", "child_guardians", ["child_user_id"])

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO child_guardians (id, parent_user_id, child_user_id)
            SELECT gen_random_uuid(), parent_id, id
            FROM users
            WHERE is_child = true AND parent_id IS NOT NULL
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_child_guardians_child", table_name="child_guardians")
    op.drop_index("ix_child_guardians_parent_child", table_name="child_guardians")
    op.drop_table("child_guardians")

"""Display name, KI-Prefs, Aufgabentyp

Revision ID: 005
Revises: 004
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, Sequence[str], None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("settings_encrypted", sa.LargeBinary(), nullable=True))
    op.add_column(
        "learning_units",
        sa.Column("task_type", sa.String(length=32), nullable=False, server_default="mixed"),
    )
    op.alter_column("learning_units", "task_type", server_default=None)


def downgrade() -> None:
    op.drop_column("learning_units", "task_type")
    op.drop_column("users", "settings_encrypted")

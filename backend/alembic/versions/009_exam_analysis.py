"""Migration 009: KI-Analyse für Schulprüfungen (Phase B)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, Sequence[str], None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("exam_results", sa.Column("analysis_encrypted", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("exam_results", "analysis_encrypted")

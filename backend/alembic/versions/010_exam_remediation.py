"""Migration 010: Nacharbeit-Einheit aus Prüfungsanalyse (Phase C)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, Sequence[str], None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "exam_results",
        sa.Column("remediation_unit_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_exam_results_remediation_unit",
        "exam_results",
        "learning_units",
        ["remediation_unit_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_exam_results_remediation_unit", "exam_results", type_="foreignkey")
    op.drop_column("exam_results", "remediation_unit_id")

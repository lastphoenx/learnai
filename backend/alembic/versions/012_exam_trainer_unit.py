"""exam trainer unit link (Prüfung → interaktiver Lerntrainer)"""

from alembic import op
import sqlalchemy as sa

revision = "012_exam_trainer_unit"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "exam_results",
        sa.Column("trainer_unit_id", sa.UUID(), nullable=True),
    )
    op.create_foreign_key(
        "fk_exam_results_trainer_unit",
        "exam_results",
        "learning_units",
        ["trainer_unit_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_exam_results_trainer_unit", "exam_results", type_="foreignkey")
    op.drop_column("exam_results", "trainer_unit_id")

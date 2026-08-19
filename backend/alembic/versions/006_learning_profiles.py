"""Learning profiles and parent-child accounts.

Revision ID: 006
Revises: 005
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "006"
down_revision: Union[str, Sequence[str], None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "learning_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("display_name", sa.String(length=80), nullable=False),
        sa.Column("settings_encrypted", sa.LargeBinary(), nullable=True),
        sa.Column("managed_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_child_profile", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
    op.create_index("ix_learning_profiles_tenant", "learning_profiles", ["tenant_id"])
    op.create_index("ix_learning_profiles_user", "learning_profiles", ["user_id"])

    op.add_column("users", sa.Column("parent_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("users", sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_child", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_foreign_key("fk_users_parent", "users", "users", ["parent_id"], ["id"])
    op.create_foreign_key(
        "fk_users_profile", "users", "learning_profiles", ["profile_id"], ["id"], use_alter=True
    )

    op.add_column("learning_units", sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_learning_units_profile",
        "learning_units",
        "learning_profiles",
        ["profile_id"],
        ["id"],
    )

    op.add_column("learning_records", sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_learning_records_profile",
        "learning_records",
        "learning_profiles",
        ["profile_id"],
        ["id"],
    )

    conn = op.get_bind()
    users = conn.execute(
        sa.text(
            "SELECT id, tenant_id, settings_encrypted FROM users WHERE settings_encrypted IS NOT NULL"
        )
    ).fetchall()
    for row in users:
        profile_id = conn.execute(sa.text("SELECT gen_random_uuid()")).scalar()
        conn.execute(
            sa.text(
                """
                INSERT INTO learning_profiles
                    (id, tenant_id, display_name, settings_encrypted, managed_by_id, user_id, is_child_profile)
                VALUES
                    (:id, :tenant_id, 'Lerner', :settings, :user_id, :user_id, false)
                """
            ),
            {
                "id": profile_id,
                "tenant_id": row.tenant_id,
                "settings": row.settings_encrypted,
                "user_id": row.id,
            },
        )
        conn.execute(
            sa.text("UPDATE users SET profile_id = :pid WHERE id = :uid"),
            {"pid": profile_id, "uid": row.id},
        )
        conn.execute(
            sa.text("UPDATE learning_units SET profile_id = :pid WHERE created_by_id = :uid"),
            {"pid": profile_id, "uid": row.id},
        )
        conn.execute(
            sa.text("UPDATE learning_records SET profile_id = :pid WHERE user_id = :uid"),
            {"pid": profile_id, "uid": row.id},
        )

    bare = conn.execute(sa.text("SELECT id, tenant_id FROM users WHERE profile_id IS NULL")).fetchall()
    for row in bare:
        profile_id = conn.execute(sa.text("SELECT gen_random_uuid()")).scalar()
        conn.execute(
            sa.text(
                """
                INSERT INTO learning_profiles
                    (id, tenant_id, display_name, managed_by_id, user_id, is_child_profile)
                VALUES
                    (:id, :tenant_id, 'Lerner', :user_id, :user_id, false)
                """
            ),
            {"id": profile_id, "tenant_id": row.tenant_id, "user_id": row.id},
        )
        conn.execute(
            sa.text("UPDATE users SET profile_id = :pid WHERE id = :uid"),
            {"pid": profile_id, "uid": row.id},
        )


def downgrade() -> None:
    op.drop_constraint("fk_learning_records_profile", "learning_records", type_="foreignkey")
    op.drop_column("learning_records", "profile_id")
    op.drop_constraint("fk_learning_units_profile", "learning_units", type_="foreignkey")
    op.drop_column("learning_units", "profile_id")
    op.drop_constraint("fk_users_profile", "users", type_="foreignkey")
    op.drop_constraint("fk_users_parent", "users", type_="foreignkey")
    op.drop_column("users", "is_child")
    op.drop_column("users", "profile_id")
    op.drop_column("users", "parent_id")
    op.drop_index("ix_learning_profiles_user", table_name="learning_profiles")
    op.drop_index("ix_learning_profiles_tenant", table_name="learning_profiles")
    op.drop_table("learning_profiles")

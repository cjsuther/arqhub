"""groups, folder visibility grants, draft author + shares

Revision ID: access_20260807
Revises: status_20260806
Create Date: 2026-08-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "access_20260807"
down_revision: Union[str, None] = "status_20260806"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ts(*cols: sa.Column) -> list[sa.Column]:
    return [
        *cols,
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    ]


def upgrade() -> None:
    op.create_table(
        "groups",
        *_ts(
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=True),
            sa.Column("name", sa.String(length=255), nullable=False),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_groups_tenant_id", "groups", ["tenant_id"])

    op.create_table(
        "user_groups",
        *_ts(
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=True),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("group_id", sa.String(length=36), nullable=False),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_groups_user_id", "user_groups", ["user_id"])
    op.create_index("ix_user_groups_group_id", "user_groups", ["group_id"])

    op.create_table(
        "group_folders",
        *_ts(
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=True),
            sa.Column("group_id", sa.String(length=36), nullable=False),
            sa.Column("folder_id", sa.String(length=36), nullable=False),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["group_id"], ["groups.id"]),
        sa.ForeignKeyConstraint(["folder_id"], ["folders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_group_folders_group_id", "group_folders", ["group_id"])
    op.create_index("ix_group_folders_folder_id", "group_folders", ["folder_id"])

    op.create_table(
        "view_shares",
        *_ts(
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("tenant_id", sa.String(length=36), nullable=True),
            sa.Column("view_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["view_id"], ["views.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_view_shares_view_id", "view_shares", ["view_id"])

    with op.batch_alter_table("views") as batch:
        batch.add_column(sa.Column("created_by", sa.String(length=36), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("views") as batch:
        batch.drop_column("created_by")
    op.drop_index("ix_view_shares_view_id", table_name="view_shares")
    op.drop_table("view_shares")
    op.drop_index("ix_group_folders_folder_id", table_name="group_folders")
    op.drop_index("ix_group_folders_group_id", table_name="group_folders")
    op.drop_table("group_folders")
    op.drop_index("ix_user_groups_group_id", table_name="user_groups")
    op.drop_index("ix_user_groups_user_id", table_name="user_groups")
    op.drop_table("user_groups")
    op.drop_index("ix_groups_tenant_id", table_name="groups")
    op.drop_table("groups")

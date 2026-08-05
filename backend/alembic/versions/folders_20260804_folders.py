"""folders + folder_id on elements/views

Revision ID: folders_20260804
Revises: pool_20260804
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "folders_20260804"
down_revision: Union[str, None] = "pool_20260804"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "folders",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.String(length=16), nullable=False),
        sa.Column("parent_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["parent_id"], ["folders.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_folders_tenant_id", "folders", ["tenant_id"])
    op.create_index("ix_folders_scope", "folders", ["scope"])
    op.create_index("ix_folders_parent_id", "folders", ["parent_id"])
    with op.batch_alter_table("elements") as batch:
        batch.add_column(sa.Column("folder_id", sa.String(length=36), nullable=True))
    with op.batch_alter_table("views") as batch:
        batch.add_column(sa.Column("folder_id", sa.String(length=36), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("views") as batch:
        batch.drop_column("folder_id")
    with op.batch_alter_table("elements") as batch:
        batch.drop_column("folder_id")
    op.drop_index("ix_folders_parent_id", table_name="folders")
    op.drop_index("ix_folders_scope", table_name="folders")
    op.drop_index("ix_folders_tenant_id", table_name="folders")
    op.drop_table("folders")

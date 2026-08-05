"""view status timestamp/author + per-approver decisions

Revision ID: status_20260806
Revises: collab_20260805
Create Date: 2026-08-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "status_20260806"
down_revision: Union[str, None] = "collab_20260805"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("views") as batch:
        batch.add_column(sa.Column("status_changed_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("status_changed_by", sa.String(length=36), nullable=True))
    op.create_table(
        "approval_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=True),
        sa.Column("approval_id", sa.String(length=36), nullable=False),
        sa.Column("approver_id", sa.String(length=36), nullable=True),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("comment", sa.String(length=1024), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["approval_id"], ["approval_requests.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_decisions_approval_id", "approval_decisions", ["approval_id"])
    op.create_index("ix_approval_decisions_tenant_id", "approval_decisions", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_approval_decisions_tenant_id", table_name="approval_decisions")
    op.drop_index("ix_approval_decisions_approval_id", table_name="approval_decisions")
    op.drop_table("approval_decisions")
    with op.batch_alter_table("views") as batch:
        batch.drop_column("status_changed_by")
        batch.drop_column("status_changed_at")

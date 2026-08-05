"""view notes (rich text) + comments table

Revision ID: collab_20260805
Revises: folders_20260804
Create Date: 2026-08-05
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "collab_20260805"
down_revision: Union[str, None] = "folders_20260804"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("views") as batch:
        batch.add_column(sa.Column("notes", sa.String(), nullable=True))
    op.create_table(
        "comments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=True),
        sa.Column("view_id", sa.String(length=36), nullable=False),
        sa.Column("author_id", sa.String(length=36), nullable=True),
        sa.Column("body", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["view_id"], ["views.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_comments_tenant_id", "comments", ["tenant_id"])
    op.create_index("ix_comments_view_id", "comments", ["view_id"])


def downgrade() -> None:
    op.drop_index("ix_comments_view_id", table_name="comments")
    op.drop_index("ix_comments_tenant_id", table_name="comments")
    op.drop_table("comments")
    with op.batch_alter_table("views") as batch:
        batch.drop_column("notes")

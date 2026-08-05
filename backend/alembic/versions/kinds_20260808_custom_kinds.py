"""custom component kinds (registry extension)

Revision ID: kinds_20260808
Revises: access_20260807
Create Date: 2026-08-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "kinds_20260808"
down_revision: Union[str, None] = "access_20260807"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "custom_kinds",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("layer", sa.String(length=32), nullable=False),
        sa.Column("archimate", sa.String(length=64), nullable=True),
        sa.Column("bpmn", sa.String(length=64), nullable=True),
        sa.Column("uml", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_custom_kinds_key"),
    )
    op.create_index("ix_custom_kinds_key", "custom_kinds", ["key"])


def downgrade() -> None:
    op.drop_index("ix_custom_kinds_key", table_name="custom_kinds")
    op.drop_table("custom_kinds")

"""view_layouts.parent for BPMN pool/lane nesting

Revision ID: pool_20260804
Revises: rls_20260730
Create Date: 2026-08-04
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "pool_20260804"
down_revision: Union[str, None] = "rls_20260730"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("view_layouts") as batch:
        batch.add_column(sa.Column("parent", sa.String(length=128), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("view_layouts") as batch:
        batch.drop_column("parent")

"""folder edit lock (locked + edit_group_id)

Revision ID: lock_20260810
Revises: notif_20260809
Create Date: 2026-08-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "lock_20260810"
down_revision: Union[str, None] = "notif_20260809"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("folders") as batch:
        batch.add_column(sa.Column("locked", sa.Boolean(), nullable=True))
        batch.add_column(sa.Column("edit_group_id", sa.String(length=36), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("folders") as batch:
        batch.drop_column("edit_group_id")
        batch.drop_column("locked")

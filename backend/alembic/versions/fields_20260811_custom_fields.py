"""custom field definitions per kind + element custom_fields

Revision ID: fields_20260811
Revises: lock_20260810
Create Date: 2026-08-11
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "fields_20260811"
down_revision: Union[str, None] = "lock_20260810"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_JSON = sa.JSON().with_variant(sa.dialects.postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("elements") as batch:
        batch.add_column(sa.Column("custom_fields", _JSON, nullable=True))
    op.create_table(
        "field_defs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tenant_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("field_type", sa.String(length=24), nullable=False),
        sa.Column("options", _JSON, nullable=True),
        sa.Column("position", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "kind", "key", name="uq_field_tenant_kind_key"),
    )
    op.create_index("ix_field_defs_kind", "field_defs", ["kind"])
    op.create_index("ix_field_defs_tenant_id", "field_defs", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_field_defs_tenant_id", table_name="field_defs")
    op.drop_index("ix_field_defs_kind", table_name="field_defs")
    op.drop_table("field_defs")
    with op.batch_alter_table("elements") as batch:
        batch.drop_column("custom_fields")

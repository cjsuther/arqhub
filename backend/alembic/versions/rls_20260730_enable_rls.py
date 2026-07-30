"""enable row level security (Postgres only)

Second-line tenant isolation (SPEC §12). Policies compare tenant_id against the
``app.arqhub_tenant_id`` GUC set per request (see app/core/tenancy.py). No FORCE:
the table owner bypasses RLS, so the app keeps working while direct access by
other roles is guarded. FORCE + a dedicated app role is a Fase 6 hardening step.

Revision ID: rls_20260730
Revises: 1c71b6843b4d
Create Date: 2026-07-30
"""
from typing import Sequence, Union

from alembic import op

revision: str = "rls_20260730"
down_revision: Union[str, None] = "1c71b6843b4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tenant-scoped tables (all carry tenant_id). 'tenants' is the root, excluded.
TABLES = [
    "users",
    "domains",
    "elements",
    "relationships",
    "views",
    "view_layouts",
    "model_versions",
    "approval_requests",
    "audit_log",
]

POLICY = "tenant_isolation"
GUC = "app.arqhub_tenant_id"


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY {POLICY} ON {table} "
            f"USING (tenant_id = current_setting('{GUC}', true))"
        )


def downgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    for table in TABLES:
        op.execute(f"DROP POLICY IF EXISTS {POLICY} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

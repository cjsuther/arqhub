"""Per-request tenant context for Postgres Row-Level Security (SPEC §12).

The app already filters every query by ``tenant_id`` explicitly (the primary
guard). RLS is the *second line*: policies compare ``tenant_id`` against the
``app.arqhub_tenant_id`` GUC set here. No-op on SQLite (dev).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

GUC = "app.arqhub_tenant_id"


def set_request_tenant(db: Session, tenant_id: str) -> None:
    """Bind the current tenant to the DB session so RLS policies can enforce it."""
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return
    db.execute(text("SELECT set_config(:guc, :tid, false)"), {"guc": GUC, "tid": tenant_id})

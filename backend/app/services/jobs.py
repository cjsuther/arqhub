"""Background jobs and enqueue helpers (SPEC §11).

Jobs run under the arq/Redis worker (``app.workers.main``). ``enqueue_*`` helpers
try Redis first and **fall back to running inline** when Redis is unavailable, so
the platform degrades gracefully in a no-Redis dev setup.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from ..core.config import settings
from ..core.database import SessionLocal
from ..models import Tenant
from .snapshots import create_model_snapshot


def run_snapshot(tenant_id: str) -> str:
    """Synchronous unit of work: snapshot one tenant's model."""
    with SessionLocal() as db:
        row = create_model_snapshot(db, tenant_id, message="daily snapshot")
    return f"model v{row.version}"


def snapshot_all_tenants() -> list[str]:
    with SessionLocal() as db:
        tenant_ids = list(db.scalars(select(Tenant.id)))
    return [run_snapshot(t) for t in tenant_ids]


async def _enqueue(func_name: str, *args) -> None:
    from arq import create_pool
    from arq.connections import RedisSettings

    pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        await pool.enqueue_job(func_name, *args)
    finally:
        await pool.close()


def enqueue_snapshot(tenant_id: str) -> str:
    """Enqueue a snapshot on Redis; run inline if Redis/arq is unavailable."""
    try:
        asyncio.run(_enqueue("job_snapshot", tenant_id))
        return "enqueued"
    except Exception:
        run_snapshot(tenant_id)
        return "inline"

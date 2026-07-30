"""arq worker (SPEC §11). Run with:  arq app.workers.main.WorkerSettings

Requires Redis (ARQHUB_REDIS_URL). The daily cron snapshots every tenant's model;
``job_snapshot`` is the on-demand variant enqueued from the API.
"""

from __future__ import annotations

from arq import cron
from arq.connections import RedisSettings

from ..core.config import settings
from ..services.jobs import run_snapshot, snapshot_all_tenants


async def job_snapshot(ctx, tenant_id: str) -> str:
    return run_snapshot(tenant_id)


async def daily_snapshot(ctx) -> list[str]:
    return snapshot_all_tenants()


class WorkerSettings:
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    functions = [job_snapshot]
    cron_jobs = [cron(daily_snapshot, hour={2}, minute=0)]  # 02:00 every day

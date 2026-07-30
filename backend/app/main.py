"""ArqHub FastAPI application (SPEC §3, §7).

In dev (SQLite) the schema is created on startup and the seed tenant/admin are
ensured. In prod the schema is owned by Alembic migrations instead.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api.v1 import router as api_v1_router
from .core.auth import ensure_seed
from .core.config import settings
from .core.database import SessionLocal, engine
from .core.ratelimit import RateLimiter
from .models import Base

_limiter = RateLimiter(settings.rate_limit_per_minute)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        ensure_seed(db)
    yield


app = FastAPI(title="ArqHub API", version="0.1.0", lifespan=lifespan)


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if settings.rate_limit_enabled and request.url.path.startswith(settings.api_prefix):
        key = request.headers.get("authorization") or (request.client.host if request.client else "anon")
        if not _limiter.check(key):
            return JSONResponse({"detail": "Rate limit exceeded."}, status_code=429)
    return await call_next(request)


app.include_router(api_v1_router, prefix=settings.api_prefix)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}

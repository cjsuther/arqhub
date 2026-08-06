"""Personal access tokens for MCP/script auth (SPEC §9, §12).

Only the SHA-256 hash is persisted. Requests carrying ``Authorization: Bearer
arqhub_...`` are authenticated as the token's user (actor_type ``mcp``).
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.auth import Principal
from ..models import ApiToken, User
from ..schemas.api import TokenCreate, TokenCreated, TokenRead

PREFIX = "arqhub_"


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _read(t: ApiToken) -> TokenRead:
    return TokenRead(
        id=t.id, name=t.name, prefix=t.prefix,
        last_used_at=t.last_used_at.isoformat() if t.last_used_at else None,
        created_at=t.created_at.isoformat() if t.created_at else "",
    )


def list_tokens(db: Session, principal: Principal) -> list[TokenRead]:
    rows = db.scalars(
        select(ApiToken).where(ApiToken.tenant_id == principal.tenant_id, ApiToken.user_id == principal.user_id)
        .order_by(ApiToken.created_at.desc())
    ).all()
    return [_read(t) for t in rows]


def create_token(db: Session, principal: Principal, payload: TokenCreate) -> TokenCreated:
    raw = PREFIX + secrets.token_urlsafe(32)
    t = ApiToken(
        tenant_id=principal.tenant_id, user_id=principal.user_id,
        name=(payload.name or "token").strip() or "token",
        token_hash=_hash(raw), prefix=raw[: len(PREFIX) + 6] + "…",
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return TokenCreated(**_read(t).model_dump(), token=raw)


def revoke_token(db: Session, principal: Principal, token_id: str) -> None:
    t = db.get(ApiToken, token_id)
    if t is None or t.tenant_id != principal.tenant_id or t.user_id != principal.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Token no encontrado.")
    db.delete(t)
    db.commit()


def authenticate_token(db: Session, raw: str) -> Principal | None:
    """Resolve a bearer PAT to a Principal, or None if unknown/invalid."""
    t = db.scalar(select(ApiToken).where(ApiToken.token_hash == _hash(raw)))
    if t is None:
        return None
    user = db.get(User, t.user_id)
    if user is None:
        return None
    t.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return Principal(
        user_id=user.id, tenant_id=user.tenant_id, email=user.email, role=user.role, actor_type="mcp"
    )

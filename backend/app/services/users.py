"""User directory queries (SPEC §7)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.auth import Principal
from ..models import User
from ..schemas.api import UserRead


def _read(u: User) -> UserRead:
    return UserRead(id=u.id, email=u.email, display_name=u.display_name, role=u.role)


def list_users(db: Session, tenant_id: str, role: str | None = None) -> list[UserRead]:
    q = select(User).where(User.tenant_id == tenant_id)
    if role:
        q = q.where(User.role == role)
    return [_read(u) for u in db.scalars(q.order_by(User.display_name))]


def get_me(db: Session, principal: Principal) -> UserRead:
    u = db.get(User, principal.user_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    return _read(u)

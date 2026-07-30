"""User endpoints (SPEC §7)."""

from __future__ import annotations

from fastapi import APIRouter

from ...core.deps import DbDep, PrincipalDep
from ...schemas.api import UserRead
from ...services import users

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(db: DbDep, principal: PrincipalDep, role: str | None = None):
    """List users of the tenant (optionally filtered by role) — approver picklist."""
    return users.list_users(db, principal.tenant_id, role)


@router.get("/me", response_model=UserRead)
def get_me(db: DbDep, principal: PrincipalDep):
    return users.get_me(db, principal)

"""User endpoints (SPEC §7, §12)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from ...core.deps import DbDep, PrincipalDep, require_role
from ...schemas.api import UserCreate, UserRead, UserUpdate
from ...services import users

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserRead])
def list_users(db: DbDep, principal: PrincipalDep, role: str | None = None):
    """List users of the tenant (optionally filtered by role) — approver picklist."""
    return users.list_users(db, principal.tenant_id, role)


@router.get("/me", response_model=UserRead)
def get_me(db: DbDep, principal: PrincipalDep):
    return users.get_me(db, principal)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(db: DbDep, payload: UserCreate, principal=Depends(require_role("admin"))):
    return users.create_user(db, principal, payload)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(db: DbDep, user_id: str, payload: UserUpdate, principal=Depends(require_role("admin"))):
    return users.update_user(db, principal, user_id, payload)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(db: DbDep, user_id: str, principal=Depends(require_role("admin"))):
    users.delete_user(db, principal, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

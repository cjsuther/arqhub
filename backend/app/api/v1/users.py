"""User endpoints (SPEC §7, §12)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from ...core.deps import DbDep, PrincipalDep, require_role
from ...schemas.api import (
    IdList,
    TokenCreate,
    TokenCreated,
    TokenRead,
    UserCreate,
    UserRead,
    UserUpdate,
)
from ...services import groups, tokens, users

router = APIRouter(prefix="/users", tags=["users"])


# --- Personal access tokens (self-service, any authenticated user) -----------
@router.get("/me/tokens", response_model=list[TokenRead])
def list_tokens(db: DbDep, principal: PrincipalDep):
    return tokens.list_tokens(db, principal)


@router.post("/me/tokens", response_model=TokenCreated, status_code=status.HTTP_201_CREATED)
def create_token(db: DbDep, body: TokenCreate, principal: PrincipalDep):
    return tokens.create_token(db, principal, body)


@router.delete("/me/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_token(db: DbDep, token_id: str, principal: PrincipalDep):
    tokens.revoke_token(db, principal, token_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=list[UserRead])
def list_users(db: DbDep, principal: PrincipalDep, role: str | None = None):
    """List users of the tenant (optionally filtered by role) — approver picklist.

    Everyone may see the roster (needed to pick approvers/assignees), but email
    addresses are only exposed to admins to limit directory harvesting.
    """
    rows = users.list_users(db, principal.tenant_id, role)
    if principal.role != "admin":
        rows = [u.model_copy(update={"email": ""}) for u in rows]
    return rows


@router.get("/me", response_model=UserRead)
def get_me(db: DbDep, principal: PrincipalDep):
    return users.get_me(db, principal)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(db: DbDep, payload: UserCreate, principal=Depends(require_role("admin"))):
    return users.create_user(db, principal, payload)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(db: DbDep, user_id: str, payload: UserUpdate, principal=Depends(require_role("admin"))):
    return users.update_user(db, principal, user_id, payload)


@router.put("/{user_id}/groups", response_model=UserRead)
def set_user_groups(db: DbDep, user_id: str, body: IdList, principal=Depends(require_role("admin"))):
    groups.set_user_groups(db, principal, user_id, body.ids)
    return users.get_user(db, principal.tenant_id, user_id)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(db: DbDep, user_id: str, principal=Depends(require_role("admin"))):
    users.delete_user(db, principal, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

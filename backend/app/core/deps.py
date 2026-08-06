"""FastAPI dependencies: DB session, current principal, tenancy, audit, RBAC."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ..models import AuditLog
from .auth import Principal, get_auth_provider
from .database import get_db
from .tenancy import set_request_tenant

DbDep = Annotated[Session, Depends(get_db)]

_ROLE_ORDER = {"viewer": 0, "editor": 1, "approver": 2, "admin": 3}


def get_principal(
    db: DbDep,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    principal: Principal | None = None
    # A personal access token (MCP/scripts) authenticates as its user.
    if token and token.startswith("arqhub_"):
        from ..services.tokens import authenticate_token

        principal = authenticate_token(db, token)
        if principal is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token inválido o revocado.")
    if principal is None:
        principal = get_auth_provider().authenticate(db, token)
    set_request_tenant(db, principal.tenant_id)  # RLS second line (Postgres only)
    return principal


PrincipalDep = Annotated[Principal, Depends(get_principal)]


def require_role(minimum: str, *, human_only: bool = False):
    """Dependency factory enforcing a minimum role (SPEC §12).

    ``human_only`` additionally rejects automation principals (personal access
    tokens / MCP, ``actor_type != "user"``). This enforces §9 at the API layer —
    the IA can create/edit drafts but must never approve, publish or delete —
    instead of relying only on which tools the MCP server chooses to expose.
    """

    def _dep(principal: PrincipalDep) -> Principal:
        if _ROLE_ORDER[principal.role] < _ROLE_ORDER[minimum]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role '{minimum}' or higher.",
            )
        if human_only and principal.actor_type != "user":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Esta acción no está permitida para tokens de automatización (IA/MCP).",
            )
        return principal

    return _dep


def write_audit(
    db: Session,
    principal: Principal,
    *,
    action: str,
    entity: str,
    entity_id: str | None = None,
    payload: dict | None = None,
) -> None:
    """Append an audit entry — every mutation, human or IA (SPEC §12)."""
    db.add(
        AuditLog(
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
            actor_type=principal.actor_type,
            action=action,
            entity=entity,
            entity_id=entity_id,
            payload=payload or {},
        )
    )

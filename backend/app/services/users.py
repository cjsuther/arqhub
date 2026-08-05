"""User directory queries + admin management (SPEC §7, §12).

Roles for Entra-provisioned users are re-synced from the token on each login
(JIT), so an in-app role change is authoritative only for local users; for Entra
users it acts as a temporary override until their next sign-in. The frontend
surfaces this distinction via ``is_entra``.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..core.auth import Principal
from ..core.deps import write_audit
from ..models import User
from ..schemas.api import UserCreate, UserRead, UserUpdate
from .groups import groups_of_user

ROLES = {"viewer", "editor", "approver", "admin"}


def _read(db: Session, u: User) -> UserRead:
    return UserRead(
        id=u.id, email=u.email, display_name=u.display_name, role=u.role,
        is_entra=bool(u.entra_oid),
        groups=groups_of_user(db, u.tenant_id, u.id),
    )


def list_users(db: Session, tenant_id: str, role: str | None = None) -> list[UserRead]:
    q = select(User).where(User.tenant_id == tenant_id)
    if role:
        q = q.where(User.role == role)
    return [_read(db, u) for u in db.scalars(q.order_by(User.display_name))]


def get_me(db: Session, principal: Principal) -> UserRead:
    u = db.get(User, principal.user_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found.")
    return _read(db, u)


def get_user(db: Session, tenant_id: str, user_id: str) -> UserRead:
    u = db.get(User, user_id)
    if u is None or u.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    return _read(db, u)


def _validate_role(role: str) -> None:
    if role not in ROLES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Rol inválido '{role}'.")


def _admin_count(db: Session, tenant_id: str) -> int:
    return db.scalar(
        select(func.count()).select_from(User).where(User.tenant_id == tenant_id, User.role == "admin")
    ) or 0


def _get_user(db: Session, tenant_id: str, user_id: str) -> User:
    u = db.get(User, user_id)
    if u is None or u.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    return u


def create_user(db: Session, principal: Principal, payload: UserCreate) -> UserRead:
    _validate_role(payload.role)
    email = payload.email.strip().lower()
    if not email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El email es obligatorio.")
    exists = db.scalar(
        select(User).where(User.tenant_id == principal.tenant_id, func.lower(User.email) == email)
    )
    if exists is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Ya existe un usuario con el email '{email}'.")
    user = User(
        tenant_id=principal.tenant_id, email=email,
        display_name=payload.display_name.strip() or email, role=payload.role,
    )
    db.add(user)
    write_audit(db, principal, action="create", entity="user", entity_id=email,
                payload={"role": payload.role})
    db.commit()
    db.refresh(user)
    return _read(db, user)


def update_user(db: Session, principal: Principal, user_id: str, payload: UserUpdate) -> UserRead:
    user = _get_user(db, principal.tenant_id, user_id)
    if payload.role is not None:
        _validate_role(payload.role)
        # Never leave the tenant without an admin.
        if user.role == "admin" and payload.role != "admin" and _admin_count(db, principal.tenant_id) <= 1:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Debe quedar al menos un administrador.")
        user.role = payload.role
    if payload.display_name is not None:
        user.display_name = payload.display_name.strip() or user.display_name
    write_audit(db, principal, action="update", entity="user", entity_id=user.email,
                payload={"role": user.role})
    db.commit()
    db.refresh(user)
    return _read(db, user)


def delete_user(db: Session, principal: Principal, user_id: str) -> None:
    user = _get_user(db, principal.tenant_id, user_id)
    if user.id == principal.user_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No podés eliminar tu propio usuario.")
    if user.role == "admin" and _admin_count(db, principal.tenant_id) <= 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Debe quedar al menos un administrador.")
    db.delete(user)
    write_audit(db, principal, action="delete", entity="user", entity_id=user.email)
    db.commit()

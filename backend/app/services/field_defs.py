"""Custom field definitions per component kind (SPEC §4.1)."""

from __future__ import annotations

import re

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.auth import Principal
from ..core.deps import write_audit
from ..models import FieldDef
from ..schemas.api import FIELD_TYPES, FieldDefCreate, FieldDefRead, FieldDefUpdate


def _read(f: FieldDef) -> FieldDefRead:
    return FieldDefRead(
        id=f.id, kind=f.kind, key=f.key, label=f.label, field_type=f.field_type,
        options=list(f.options or []), position=f.position or 0,
    )


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")


def list_fields(db: Session, tenant_id: str, kind: str | None = None) -> list[FieldDefRead]:
    q = select(FieldDef).where(FieldDef.tenant_id == tenant_id)
    if kind:
        q = q.where(FieldDef.kind == kind)
    return [_read(f) for f in db.scalars(q.order_by(FieldDef.kind, FieldDef.position, FieldDef.label))]


def create_field(db: Session, principal: Principal, kind: str, payload: FieldDefCreate) -> FieldDefRead:
    key = _slug(payload.key)
    if not key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La clave del campo es obligatoria.")
    if payload.field_type not in FIELD_TYPES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Tipo de campo inválido '{payload.field_type}'.")
    exists = db.scalar(
        select(FieldDef).where(FieldDef.tenant_id == principal.tenant_id, FieldDef.kind == kind, FieldDef.key == key)
    )
    if exists is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Ya existe un campo '{key}' para '{kind}'.")
    f = FieldDef(
        tenant_id=principal.tenant_id, kind=kind, key=key, label=payload.label.strip() or key,
        field_type=payload.field_type, options=[o for o in payload.options if o.strip()], position=payload.position,
    )
    db.add(f)
    write_audit(db, principal, action="create", entity="field", entity_id=f"{kind}.{key}")
    db.commit()
    db.refresh(f)
    return _read(f)


def _get(db: Session, tenant_id: str, field_id: str) -> FieldDef:
    f = db.get(FieldDef, field_id)
    if f is None or f.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Campo no encontrado.")
    return f


def update_field(db: Session, principal: Principal, field_id: str, payload: FieldDefUpdate) -> FieldDefRead:
    f = _get(db, principal.tenant_id, field_id)
    if payload.label is not None:
        f.label = payload.label.strip() or f.label
    if payload.field_type is not None:
        if payload.field_type not in FIELD_TYPES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Tipo inválido '{payload.field_type}'.")
        f.field_type = payload.field_type
    if payload.options is not None:
        f.options = [o for o in payload.options if o.strip()]
    if payload.position is not None:
        f.position = payload.position
    write_audit(db, principal, action="update", entity="field", entity_id=f"{f.kind}.{f.key}")
    db.commit()
    return _read(f)


def delete_field(db: Session, principal: Principal, field_id: str) -> None:
    f = _get(db, principal.tenant_id, field_id)
    db.delete(f)
    write_audit(db, principal, action="delete", entity="field", entity_id=f"{f.kind}.{f.key}")
    db.commit()

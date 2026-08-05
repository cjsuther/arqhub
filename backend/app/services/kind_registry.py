"""Persisted extensions to the type registry matrix (SPEC §4.2).

Custom kinds are loaded into the live registry at startup and whenever one is
added, so validation, exporters and the ``/meta/registry`` snapshot all see them.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..core.auth import Principal
from ..core.deps import write_audit
from ..models import CustomKind
from ..schemas.api import KindCreate
from .dsl.registry import (
    CUSTOM_KINDS,
    KIND_MAPPINGS,
    Lang,
    register_kind,
    registry_snapshot,
    unregister_kind,
)

VALID_LAYERS = {"business", "application", "technology", "motivation", "strategy", "implementation", "physical"}


def load_custom_kinds(db: Session) -> None:
    """Register all persisted custom kinds into the live registry (call at startup)."""
    for ck in db.scalars(select(CustomKind)).all():
        register_kind(ck.key, ck.layer, {Lang.archimate: ck.archimate, Lang.bpmn: ck.bpmn, Lang.uml: ck.uml})


def add_custom_kind(db: Session, principal: Principal, payload: KindCreate) -> dict:
    key = payload.key.strip().lower()
    if not key:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La clave del componente es obligatoria.")
    if key in KIND_MAPPINGS and key not in CUSTOM_KINDS:
        raise HTTPException(status.HTTP_409_CONFLICT, f"'{key}' es un tipo integrado y no se puede redefinir.")
    if payload.layer not in VALID_LAYERS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Capa inválida '{payload.layer}'.")
    a, b, u = (payload.archimate or None), (payload.bpmn or None), (payload.uml or None)
    if not (a or b or u):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El componente debe existir en al menos un lenguaje.")

    existing = db.scalar(select(CustomKind).where(CustomKind.key == key))
    if existing is None:
        db.add(CustomKind(key=key, layer=payload.layer, archimate=a, bpmn=b, uml=u))
    else:
        existing.layer, existing.archimate, existing.bpmn, existing.uml = payload.layer, a, b, u
    register_kind(key, payload.layer, {Lang.archimate: a, Lang.bpmn: b, Lang.uml: u})
    write_audit(db, principal, action="upsert", entity="kind", entity_id=key)
    db.commit()
    return registry_snapshot()


def delete_custom_kind(db: Session, principal: Principal, key: str) -> dict:
    if not unregister_kind(key):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Solo se pueden eliminar componentes personalizados.")
    db.execute(delete(CustomKind).where(CustomKind.key == key))
    write_audit(db, principal, action="delete", entity="kind", entity_id=key)
    db.commit()
    return registry_snapshot()

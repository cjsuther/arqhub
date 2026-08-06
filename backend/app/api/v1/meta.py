"""Registry + DSL schema endpoints — the SSOT consumed by the frontend (SPEC §15)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from ...core.deps import DbDep, PrincipalDep, require_role
from ...schemas.api import FieldDefCreate, FieldDefRead, FieldDefUpdate, KindCreate
from ...services import field_defs, kind_registry
from ...services.dsl.registry import registry_snapshot
from ...services.dsl.schema import DslDocument

router = APIRouter(tags=["meta"])


@router.get("/meta/registry")
def get_registry() -> dict:
    """Canonical kinds, relations, aliases and per-language mappings (SPEC §4.2)."""
    return registry_snapshot()


@router.post("/meta/kinds")
def add_kind(db: DbDep, payload: KindCreate, principal=Depends(require_role("admin"))) -> dict:
    """Add/replace a custom component kind and its per-language mappings (SPEC §4.2)."""
    return kind_registry.add_custom_kind(db, principal, payload)


@router.delete("/meta/kinds/{key}")
def delete_kind(db: DbDep, key: str, principal=Depends(require_role("admin"))) -> dict:
    return kind_registry.delete_custom_kind(db, principal, key)


# --- Custom fields per kind (SPEC §4.1) --------------------------------------
@router.get("/meta/fields", response_model=list[FieldDefRead])
def list_fields(db: DbDep, principal: PrincipalDep, kind: str | None = None):
    return field_defs.list_fields(db, principal.tenant_id, kind)


@router.post("/meta/kinds/{kind}/fields", response_model=FieldDefRead, status_code=status.HTTP_201_CREATED)
def create_field(db: DbDep, kind: str, payload: FieldDefCreate, principal=Depends(require_role("admin"))):
    return field_defs.create_field(db, principal, kind, payload)


@router.patch("/meta/fields/{field_id}", response_model=FieldDefRead)
def update_field(db: DbDep, field_id: str, payload: FieldDefUpdate, principal=Depends(require_role("admin"))):
    return field_defs.update_field(db, principal, field_id, payload)


@router.delete("/meta/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(db: DbDep, field_id: str, principal=Depends(require_role("admin"))):
    field_defs.delete_field(db, principal, field_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/dsl/schema")
def get_dsl_schema() -> dict:
    """JSON Schema of the DSL document, for LLMs to consume (SPEC §5.1)."""
    return DslDocument.model_json_schema()

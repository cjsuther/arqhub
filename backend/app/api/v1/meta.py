"""Registry + DSL schema endpoints — the SSOT consumed by the frontend (SPEC §15)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...core.deps import DbDep, require_role
from ...schemas.api import KindCreate
from ...services import kind_registry
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


@router.get("/dsl/schema")
def get_dsl_schema() -> dict:
    """JSON Schema of the DSL document, for LLMs to consume (SPEC §5.1)."""
    return DslDocument.model_json_schema()

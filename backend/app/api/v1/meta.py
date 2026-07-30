"""Registry + DSL schema endpoints — the SSOT consumed by the frontend (SPEC §15)."""

from __future__ import annotations

from fastapi import APIRouter

from ...services.dsl.registry import registry_snapshot
from ...services.dsl.schema import DslDocument

router = APIRouter(tags=["meta"])


@router.get("/meta/registry")
def get_registry() -> dict:
    """Canonical kinds, relations, aliases and per-language mappings (SPEC §4.2)."""
    return registry_snapshot()


@router.get("/dsl/schema")
def get_dsl_schema() -> dict:
    """JSON Schema of the DSL document, for LLMs to consume (SPEC §5.1)."""
    return DslDocument.model_json_schema()

"""DSL import/export at the persistence boundary (SPEC §7 /dsl)."""

from __future__ import annotations

from fastapi import HTTPException, status

from ..core.auth import Principal
from ..core.deps import write_audit
from ..schemas.api import ImportReport
from .dsl import DslParseError, apply_document, export_dsl, load_dsl
from .repository import load_graph, sync_graph


def import_dsl(db, principal: Principal, text: str, *, dry_run: bool, replace: bool) -> ImportReport:
    try:
        doc = load_dsl(text)
    except DslParseError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    graph = load_graph(db, principal.tenant_id)
    result = apply_document(graph, doc, replace=replace)

    applied = False
    if result.validation.ok and not dry_run:
        sync_graph(db, principal.tenant_id, result.graph)
        write_audit(
            db, principal, action="import_dsl", entity="model",
            payload={"replace": replace, "diff": result.diff.model_dump(mode="json")},
        )
        db.commit()
        applied = True

    return ImportReport(applied=applied, dry_run=dry_run, validation=result.validation, diff=result.diff)


def export_model(db, tenant_id: str) -> str:
    return export_dsl(load_graph(db, tenant_id))

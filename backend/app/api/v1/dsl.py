"""DSL import/export endpoints (SPEC §7 /dsl)."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Response

from ...core.deps import DbDep, PrincipalDep, require_role
from ...schemas.api import ImportReport
from ...services import model_io

router = APIRouter(prefix="/dsl", tags=["dsl"])


@router.get("/export", response_class=Response)
def export_dsl(db: DbDep, principal: PrincipalDep) -> Response:
    """Export the whole model as DSL YAML (SPEC §7)."""
    yaml_text = model_io.export_model(db, principal.tenant_id)
    return Response(content=yaml_text, media_type="application/x-yaml")


@router.post("/import", response_model=ImportReport)
def import_dsl(
    db: DbDep,
    body: str = Body(..., media_type="text/plain"),
    dry_run: bool = False,
    replace: bool = False,
    principal=Depends(require_role("editor")),
) -> ImportReport:
    """Apply a DSL document (model or patch). ``dry_run`` validates without persisting."""
    return model_io.import_dsl(db, principal, body, dry_run=dry_run, replace=replace)

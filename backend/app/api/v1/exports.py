"""Standard-format export endpoints (SPEC §7)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Response, status

from ...core.deps import DbDep, PrincipalDep
from ...services import exports

router = APIRouter(prefix="/export", tags=["export"])


def _export(db, tenant_id: str, view: str, fmt: str) -> Response:
    content, media_type = exports.export_view(db, tenant_id, view, fmt)
    return Response(content=content, media_type=media_type)


@router.get("/archimate", response_class=Response)
def export_archimate(db: DbDep, principal: PrincipalDep, view: str) -> Response:
    """ArchiMate Open Exchange XML (imports into Archi)."""
    return _export(db, principal.tenant_id, view, "archimate")


@router.get("/bpmn", response_class=Response)
def export_bpmn(db: DbDep, principal: PrincipalDep, view: str) -> Response:
    """BPMN 2.0 XML with BPMNDI (opens in Camunda Modeler)."""
    return _export(db, principal.tenant_id, view, "bpmn")


@router.get("/xmi", response_class=Response)
def export_xmi(db: DbDep, principal: PrincipalDep, view: str) -> Response:
    """XMI (UML 2.5)."""
    return _export(db, principal.tenant_id, view, "xmi")


@router.get("/mermaid", response_class=Response)
def export_mermaid(db: DbDep, principal: PrincipalDep, view: str) -> Response:
    """Mermaid flowchart (text) — compact, LLM-friendly, renders in Markdown."""
    return _export(db, principal.tenant_id, view, "mermaid")


@router.get("/image", response_class=Response)
def export_image(
    db: DbDep, principal: PrincipalDep, view: str, format: str = Query("svg")
) -> Response:
    if format == "png":
        raise HTTPException(
            status.HTTP_501_NOT_IMPLEMENTED, "PNG rasterisation not implemented yet; use format=svg."
        )
    return _export(db, principal.tenant_id, view, "svg")

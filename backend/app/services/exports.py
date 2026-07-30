"""Standard-format export orchestration (SPEC §7 /export/*, Fase 3).

Resolves a view's subgraph and node positions (layout or grid fallback), then
dispatches to the ArchiMate / BPMN / XMI / SVG exporter.
"""

from __future__ import annotations

import math

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import View, ViewLayout
from .dsl import ModelGraph
from .dsl.graph import Element, Relation
from .dsl.schema import ViewDef
from .exporters.archimate_xml import export_archimate
from .exporters.bpmn_xml import export_bpmn
from .exporters.svg import render_view_svg
from .exporters.xmi import export_xmi
from .repository import load_graph

BOX_W, BOX_H, GAP_X, GAP_Y, MARGIN = 170, 64, 60, 60, 40

_XML = "application/xml"
FORMATS = {
    "archimate": _XML,
    "bpmn": _XML,
    "xmi": _XML,
    "svg": "image/svg+xml",
}


def _subgraph(graph: ModelGraph, view: ViewDef) -> tuple[list[Element], list[Relation]]:
    included = list(view.include.elements)
    els = [graph.elements[s] for s in included if s in graph.elements]
    present = set(s for s in included if s in graph.elements)
    rels: list[Relation] = []
    for r in graph.relations.values():
        if isinstance(view.include.relations, list):
            keep = r.id in view.include.relations
        else:
            keep = r.from_ in present and r.to in present
        if keep and r.from_ in present and r.to in present:
            rels.append(r)
    return els, rels


def _positions(
    db: Session, view_id: str, els: list[Element]
) -> dict[str, tuple[float, float, float, float]]:
    """Persisted layout, falling back to a deterministic grid for missing nodes."""
    saved = {
        l.element_slug: (l.x, l.y, l.w or BOX_W, l.h or BOX_H)
        for l in db.query(ViewLayout).filter(ViewLayout.view_id == view_id).all()
    }
    cols = max(1, math.ceil(math.sqrt(len(els)))) if els else 1
    out: dict[str, tuple[float, float, float, float]] = {}
    for i, e in enumerate(els):
        if e.slug in saved:
            out[e.slug] = saved[e.slug]
        else:
            row, col = divmod(i, cols)
            out[e.slug] = (
                MARGIN + col * (BOX_W + GAP_X), MARGIN + row * (BOX_H + GAP_Y), BOX_W, BOX_H
            )
    return out


def export_view(db: Session, tenant_id: str, slug: str, fmt: str) -> tuple[str, str]:
    if fmt not in FORMATS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown export format '{fmt}'.")

    graph = load_graph(db, tenant_id)
    view = graph.views.get(slug)
    if view is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"View '{slug}' not found.")

    if fmt == "svg":
        return render_view_svg(graph, view), FORMATS[fmt]

    row = db.scalar(select(View).where(View.tenant_id == tenant_id, View.slug == slug))
    els, rels = _subgraph(graph, view)
    positions = _positions(db, row.id, els)

    if fmt == "archimate":
        return export_archimate(els, rels, view, positions), FORMATS[fmt]
    if fmt == "bpmn":
        return export_bpmn(els, rels, view, positions), FORMATS[fmt]
    return export_xmi(els, rels, view, positions), FORMATS[fmt]

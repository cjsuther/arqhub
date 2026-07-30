"""View read + versioning (snapshot & semantic diff) — SPEC §7, §11."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select

from sqlalchemy import delete

from ..core.auth import Principal
from ..core.deps import write_audit
from ..models import ModelVersion, View, ViewLayout
from ..schemas.api import (
    LayoutNode,
    LayoutPut,
    ViewCreate,
    ViewGraphRead,
    ViewRead,
    ViewUpdate,
    VersionRead,
)
from .catalog import _element_read, _relation_read
from .dsl import ModelGraph, apply_document, diff_graphs, graph_to_dict
from .dsl.schema import DslDocument, ViewDef, ViewInclude
from .exporters import render_view_svg
from .repository import load_graph, sync_graph


def _view_read(v: View) -> ViewRead:
    return ViewRead(
        slug=v.slug, name=v.name, lang=v.lang, viewpoint=v.viewpoint,
        include=v.include or {}, status=v.status, current_version=v.current_version,
    )


def list_views(db, tenant_id: str) -> list[ViewRead]:
    rows = db.scalars(select(View).where(View.tenant_id == tenant_id)).all()
    return [_view_read(v) for v in rows]


def _get_view_row(db, tenant_id: str, slug: str) -> View:
    v = db.scalar(select(View).where(View.tenant_id == tenant_id, View.slug == slug))
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"View '{slug}' not found.")
    return v


def get_view(db, tenant_id: str, slug: str) -> ViewRead:
    return _view_read(_get_view_row(db, tenant_id, slug))


def render_view(db, tenant_id: str, slug: str) -> str:
    graph = load_graph(db, tenant_id)
    view = graph.views.get(slug)
    if view is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"View '{slug}' not found.")
    return render_view_svg(graph, view)


def get_view_graph(db, tenant_id: str, slug: str) -> ViewGraphRead:
    """Resolve everything the canvas needs to render a view in one call."""
    row = _get_view_row(db, tenant_id, slug)
    graph = load_graph(db, tenant_id)
    sub = _view_subgraph(graph, graph.views[slug])
    layout = [
        LayoutNode(element=l.element_slug, x=l.x, y=l.y, w=l.w, h=l.h, style=l.style or {})
        for l in db.query(ViewLayout).filter(ViewLayout.view_id == row.id).all()
    ]
    return ViewGraphRead(
        view=_view_read(row),
        elements=[_element_read(el) for el in sub.elements.values()],
        relations=[_relation_read(rel) for rel in sub.relations.values()],
        layout=layout,
    )


def put_layout(db, principal: Principal, slug: str, payload: LayoutPut) -> None:
    """Persist node positions (presentation only — never touches the model)."""
    row = _get_view_row(db, principal.tenant_id, slug)
    db.execute(delete(ViewLayout).where(ViewLayout.view_id == row.id))
    for node in payload.nodes:
        db.add(
            ViewLayout(
                tenant_id=principal.tenant_id, view_id=row.id, element_slug=node.element,
                x=node.x, y=node.y, w=node.w, h=node.h, style=node.style,
            )
        )
    write_audit(db, principal, action="put_layout", entity="view", entity_id=slug,
                payload={"nodes": len(payload.nodes)})
    db.commit()


def create_view(db, principal: Principal, payload: ViewCreate) -> ViewRead:
    graph = load_graph(db, principal.tenant_id)
    if payload.slug in graph.views:
        raise HTTPException(status.HTTP_409_CONFLICT, f"View '{payload.slug}' already exists.")
    view_def = ViewDef(
        id=payload.slug, name=payload.name, lang=payload.lang, viewpoint=payload.viewpoint,
        include=ViewInclude(**payload.include.model_dump()),
    )
    result = apply_document(graph, DslDocument(views=[view_def]))
    if not result.validation.ok:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": [i.model_dump() for i in result.validation.errors]},
        )
    sync_graph(db, principal.tenant_id, result.graph)
    write_audit(db, principal, action="create", entity="view", entity_id=payload.slug)
    db.commit()
    return get_view(db, principal.tenant_id, payload.slug)


def update_view(db, principal: Principal, slug: str, payload: ViewUpdate) -> ViewRead:
    row = _get_view_row(db, principal.tenant_id, slug)
    changes = payload.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(row, field, value)
    write_audit(db, principal, action="update", entity="view", entity_id=slug, payload={"fields": list(changes)})
    db.commit()
    return _view_read(row)


def _view_subgraph(graph: ModelGraph, view: ViewDef) -> ModelGraph:
    """Elements the view includes + the relations among them (SPEC §4.1 include)."""
    sub = ModelGraph()
    included = set(view.include.elements)
    for slug in included:
        if slug in graph.elements:
            sub.elements[slug] = graph.elements[slug]
    for rel in graph.relations.values():
        if isinstance(view.include.relations, list):
            keep = rel.id in view.include.relations
        else:  # "auto": relations whose endpoints are both included
            keep = rel.from_ in included and rel.to in included
        if keep:
            sub.relations[rel.id] = rel
    sub.views[view.id] = view
    return sub


def _graph_from_snapshot(snapshot: dict) -> ModelGraph:
    doc = DslDocument.model_validate(snapshot)
    return apply_document(None, doc).graph


def create_view_version(db, principal: Principal, slug: str, message: str | None) -> VersionRead:
    row = _get_view_row(db, principal.tenant_id, slug)
    graph = load_graph(db, principal.tenant_id)
    snapshot = graph_to_dict(_view_subgraph(graph, graph.views[slug]))

    last = db.scalar(
        select(ModelVersion)
        .where(ModelVersion.tenant_id == principal.tenant_id, ModelVersion.scope == "view", ModelVersion.scope_id == slug)
        .order_by(ModelVersion.version.desc())
    )
    version = (last.version if last else 0) + 1
    db.add(ModelVersion(
        tenant_id=principal.tenant_id, scope="view", scope_id=slug, version=version,
        snapshot=snapshot, message=message, author_id=principal.user_id,
    ))
    row.current_version = version
    write_audit(db, principal, action="commit_version", entity="view", entity_id=slug, payload={"version": version})
    db.commit()
    return VersionRead(version=version, scope="view", scope_id=slug, message=message)


def list_view_versions(db, tenant_id: str, slug: str) -> list[VersionRead]:
    _get_view_row(db, tenant_id, slug)
    rows = db.scalars(
        select(ModelVersion)
        .where(ModelVersion.tenant_id == tenant_id, ModelVersion.scope == "view", ModelVersion.scope_id == slug)
        .order_by(ModelVersion.version)
    ).all()
    return [VersionRead(version=r.version, scope=r.scope, scope_id=r.scope_id, message=r.message) for r in rows]


def diff_view_versions(db, tenant_id: str, slug: str, from_v: int, to_v: int):
    _get_view_row(db, tenant_id, slug)

    def _snapshot(version: int) -> dict:
        r = db.scalar(
            select(ModelVersion).where(
                ModelVersion.tenant_id == tenant_id, ModelVersion.scope == "view",
                ModelVersion.scope_id == slug, ModelVersion.version == version,
            )
        )
        if r is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Version {version} of view '{slug}' not found.")
        return r.snapshot

    before = _graph_from_snapshot(_snapshot(from_v))
    after = _graph_from_snapshot(_snapshot(to_v))
    return diff_graphs(before, after)

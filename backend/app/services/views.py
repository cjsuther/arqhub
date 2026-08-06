"""View read + versioning (snapshot & semantic diff) — SPEC §7, §11."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select

from sqlalchemy import delete

from ..core.auth import Principal
from ..core.deps import write_audit
from ..models import ApprovalRequest, ModelVersion, User, View, ViewLayout, ViewShare
from . import access
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


def _name_of(db, tenant_id: str, user_id: str | None) -> str | None:
    if not user_id:
        return None
    u = db.scalar(select(User).where(User.tenant_id == tenant_id, User.id == user_id))
    return u.display_name if u else user_id


def _view_read(db, tenant_id: str, v: View) -> ViewRead:
    return ViewRead(
        slug=v.slug, name=v.name, lang=v.lang, viewpoint=v.viewpoint,
        include=v.include or {}, status=v.status,
        status_changed_at=v.status_changed_at.isoformat() if v.status_changed_at else None,
        status_changed_by=v.status_changed_by, status_changed_by_name=_name_of(db, tenant_id, v.status_changed_by),
        created_by=v.created_by, created_by_name=_name_of(db, tenant_id, v.created_by),
        current_version=v.current_version, folder_id=v.folder_id, notes=v.notes,
    )


def set_view_status(db, view_row: View, status: str, principal: Principal) -> None:
    """Move a view to a new status, recording who did it and when (SPEC §11)."""
    from datetime import datetime, timezone
    view_row.status = status
    view_row.status_changed_at = datetime.now(timezone.utc)
    view_row.status_changed_by = principal.user_id


def _assert_visible(db, principal: Principal, row: View) -> None:
    accessible = access.accessible_folder_ids(db, principal)
    shares = set(db.scalars(select(ViewShare.user_id).where(ViewShare.view_id == row.id)).all())
    if not access.can_see_view(principal, row, accessible, shares):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"View '{row.slug}' not found.")


def list_views(db, principal: Principal) -> list[ViewRead]:
    rows = db.scalars(select(View).where(View.tenant_id == principal.tenant_id)).all()
    accessible = access.accessible_folder_ids(db, principal)
    shares = access.view_shares(db, principal.tenant_id)
    visible = [v for v in rows if access.can_see_view(principal, v, accessible, shares.get(v.id, set()))]
    return [_view_read(db, principal.tenant_id, v) for v in visible]


def get_view_shares(db, tenant_id: str, slug: str) -> list[str]:
    row = _get_view_row(db, tenant_id, slug)
    return list(db.scalars(select(ViewShare.user_id).where(ViewShare.view_id == row.id)).all())


def set_view_shares(db, principal: Principal, slug: str, user_ids: list[str]) -> list[str]:
    from .notifications import get_notifier, store

    row = _get_view_row(db, principal.tenant_id, slug)
    previous = set(db.scalars(select(ViewShare.user_id).where(ViewShare.view_id == row.id)).all())
    valid = set(db.scalars(select(User.id).where(User.tenant_id == principal.tenant_id)).all())
    db.execute(delete(ViewShare).where(ViewShare.view_id == row.id))
    kept: list[str] = []
    for uid in dict.fromkeys(user_ids):
        if uid in valid and uid != row.created_by:
            db.add(ViewShare(tenant_id=principal.tenant_id, view_id=row.id, user_id=uid))
            kept.append(uid)
    write_audit(db, principal, action="share", entity="view", entity_id=slug, payload={"users": user_ids})
    db.commit()

    # Notify only the newly-added users.
    added = [u for u in kept if u not in previous]
    if added:
        names = {u.id: u.display_name for u in db.scalars(select(User).where(User.tenant_id == principal.tenant_id)).all()}
        get_notifier().draft_shared(
            view_slug=slug, view_name=row.name,
            shared_by=names.get(principal.user_id, principal.email),
            users=[names.get(u, u) for u in added],
        )
        store.record(
            db, principal.tenant_id, added,
            kind="draft_shared", title=f"Compartieron un borrador: {row.name}",
            body=f"{names.get(principal.user_id, principal.email)} te compartió este borrador.",
            view_slug=slug,
        )
    return get_view_shares(db, principal.tenant_id, slug)


def _get_view_row(db, tenant_id: str, slug: str) -> View:
    v = db.scalar(select(View).where(View.tenant_id == tenant_id, View.slug == slug))
    if v is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"View '{slug}' not found.")
    return v


def get_view(db, tenant_id: str, slug: str) -> ViewRead:
    v = _get_view_row(db, tenant_id, slug)
    return _view_read(db, tenant_id, v)


def _layout_map(db, view_id: str) -> dict:
    return {
        l.element_slug: {"x": l.x, "y": l.y, "w": l.w, "h": l.h, "parent": l.parent}
        for l in db.query(ViewLayout).filter(ViewLayout.view_id == view_id).all()
    }


def render_view(db, principal: Principal, slug: str) -> str:
    row = _get_view_row(db, principal.tenant_id, slug)
    _assert_visible(db, principal, row)
    graph = load_graph(db, principal.tenant_id)
    view = graph.views.get(slug)
    if view is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"View '{slug}' not found.")
    return render_view_svg(graph, view, _layout_map(db, row.id))


def get_view_graph(db, principal: Principal, slug: str) -> ViewGraphRead:
    """Resolve everything the canvas needs to render a view in one call."""
    tenant_id = principal.tenant_id
    row = _get_view_row(db, tenant_id, slug)
    _assert_visible(db, principal, row)
    graph = load_graph(db, tenant_id)
    sub = _view_subgraph(graph, graph.views[slug])
    layout = [
        LayoutNode(element=l.element_slug, x=l.x, y=l.y, w=l.w, h=l.h, parent=l.parent, style=l.style or {})
        for l in db.query(ViewLayout).filter(ViewLayout.view_id == row.id).all()
    ]
    return ViewGraphRead(
        view=_view_read(db, tenant_id, row),
        elements=[_element_read(el) for el in sub.elements.values()],
        relations=[_relation_read(rel) for rel in sub.relations.values()],
        layout=layout,
    )


def put_layout(db, principal: Principal, slug: str, payload: LayoutPut) -> None:
    """Persist node positions (presentation only — never touches the model)."""
    row = _get_view_row(db, principal.tenant_id, slug)
    access.assert_can_edit_folder(db, principal, row.folder_id)  # respect folder edit lock
    db.execute(delete(ViewLayout).where(ViewLayout.view_id == row.id))
    for node in payload.nodes:
        db.add(
            ViewLayout(
                tenant_id=principal.tenant_id, view_id=row.id, element_slug=node.element,
                x=node.x, y=node.y, w=node.w, h=node.h, parent=node.parent, style=node.style,
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
    row = _get_view_row(db, principal.tenant_id, payload.slug)
    set_view_status(db, row, "draft", principal)
    row.created_by = principal.user_id  # author owns the draft (SPEC §12)
    write_audit(db, principal, action="create", entity="view", entity_id=payload.slug)
    db.commit()
    return get_view(db, principal.tenant_id, payload.slug)


def set_view_folder(db, principal: Principal, slug: str, folder_id: str | None) -> ViewRead:
    row = _get_view_row(db, principal.tenant_id, slug)
    access.assert_can_edit_folder(db, principal, row.folder_id)  # source
    access.assert_can_edit_folder(db, principal, folder_id)  # target
    row.folder_id = folder_id
    write_audit(db, principal, action="move_folder", entity="view", entity_id=slug,
                payload={"folder_id": folder_id})
    db.commit()
    return _view_read(db, principal.tenant_id, row)


def update_view(db, principal: Principal, slug: str, payload: ViewUpdate) -> ViewRead:
    row = _get_view_row(db, principal.tenant_id, slug)
    access.assert_can_edit_folder(db, principal, row.folder_id)  # respect folder edit lock
    changes = payload.model_dump(exclude_none=True)

    # Editing an in-review view cancels its pending request and returns to draft
    # (SPEC §11), unless the caller is explicitly changing the status or only
    # touching presentation-side documentation (notes never affect the model).
    model_changes = {k for k in changes if k not in {"notes"}}
    if row.status == "in_review" and "status" not in changes and model_changes:
        for ar in db.scalars(
            select(ApprovalRequest).where(
                ApprovalRequest.view_id == row.id, ApprovalRequest.status == "pending"
            )
        ):
            ar.status = "cancelled"
        set_view_status(db, row, "draft", principal)

    for field, value in changes.items():
        setattr(row, field, value)
    write_audit(db, principal, action="update", entity="view", entity_id=slug, payload={"fields": list(changes)})
    db.commit()
    return _view_read(db, principal.tenant_id, row)


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

"""Bridge between persisted rows and the pure DSL ``ModelGraph``.

``load_graph`` builds an in-memory graph from the DB (so the DSL engine can
validate/export/diff), and ``sync_graph`` writes a graph back — upserting present
entities and soft-deleting the ones a patch/replace removed. Keeping the mapping
here means the DSL layer never imports SQLAlchemy.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Domain, Element, Relationship, View
from .dsl import ModelGraph
from .dsl.schema import ElementDef, RelationDef, ViewDef, ViewInclude


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _domain_id_to_slug(db: Session, tenant_id: str) -> dict[str, str]:
    rows = db.scalars(select(Domain).where(Domain.tenant_id == tenant_id)).all()
    return {d.id: d.slug for d in rows}


def _ensure_domain(db: Session, tenant_id: str, slug: str | None, cache: dict[str, Domain]) -> str | None:
    if not slug:
        return None
    if slug in cache:
        return cache[slug].id
    dom = db.scalar(
        select(Domain).where(Domain.tenant_id == tenant_id, Domain.slug == slug)
    )
    if dom is None:
        dom = Domain(tenant_id=tenant_id, slug=slug, name=slug)
        db.add(dom)
        db.flush()
    cache[slug] = dom
    return dom.id


def load_graph(db: Session, tenant_id: str) -> ModelGraph:
    """Build a ModelGraph from all non-deleted rows of a tenant."""
    graph = ModelGraph()
    dom_slug = _domain_id_to_slug(db, tenant_id)

    elements = db.scalars(
        select(Element).where(Element.tenant_id == tenant_id, Element.deleted_at.is_(None))
    ).all()
    for el in elements:
        graph.add_element(
            el.slug,
            ElementDef(
                name=el.name,
                kind=el.kind,
                domain=dom_slug.get(el.domain_id),
                owner=el.owner_id,
                description=el.description,
                lifecycle=el.lifecycle,
                tags=list(el.tags or []),
                properties=dict(el.properties or {}),
                mappings=dict(el.mappings or {}),
            ),
        )

    relations = db.scalars(
        select(Relationship).where(Relationship.tenant_id == tenant_id, Relationship.deleted_at.is_(None))
    ).all()
    for rel in relations:
        graph.add_relation(
            RelationDef.model_validate(
                {
                    "id": rel.slug,
                    "from": rel.from_element,
                    "to": rel.to_element,
                    "kind": rel.kind,
                    "label": rel.label,
                    "properties": dict(rel.properties or {}),
                }
            )
        )

    views = db.scalars(select(View).where(View.tenant_id == tenant_id)).all()
    for v in views:
        inc = v.include or {}
        graph.add_view(
            ViewDef(
                id=v.slug,
                name=v.name,
                lang=v.lang,
                viewpoint=v.viewpoint,
                include=ViewInclude(
                    elements=list(inc.get("elements", [])),
                    relations=inc.get("relations", "auto"),
                ),
            )
        )
    return graph


def sync_graph(db: Session, tenant_id: str, graph: ModelGraph) -> None:
    """Persist ``graph``: upsert its entities, soft-delete removed elements/relations."""
    dom_cache: dict[str, Domain] = {}

    db_elements = {
        e.slug: e
        for e in db.scalars(select(Element).where(Element.tenant_id == tenant_id)).all()
    }
    for slug, el in graph.elements.items():
        row = db_elements.get(slug)
        domain_id = _ensure_domain(db, tenant_id, el.domain, dom_cache)
        fields = dict(
            name=el.name,
            kind=el.kind,
            domain_id=domain_id,
            owner_id=el.owner,
            description=el.description,
            lifecycle=el.lifecycle.value,
            tags=list(el.tags),
            properties=dict(el.properties),
            mappings=dict(el.mappings),
            deleted_at=None,
        )
        if row is None:
            db.add(Element(tenant_id=tenant_id, slug=slug, **fields))
        else:
            for k, val in fields.items():
                setattr(row, k, val)
    for slug, row in db_elements.items():
        if slug not in graph.elements and row.deleted_at is None:
            row.deleted_at = _now()

    db_relations = {
        r.slug: r
        for r in db.scalars(select(Relationship).where(Relationship.tenant_id == tenant_id)).all()
    }
    for rid, rel in graph.relations.items():
        row = db_relations.get(rid)
        fields = dict(
            from_element=rel.from_,
            to_element=rel.to,
            kind=rel.kind,
            label=rel.label,
            properties=dict(rel.properties),
            deleted_at=None,
        )
        if row is None:
            db.add(Relationship(tenant_id=tenant_id, slug=rid, **fields))
        else:
            for k, val in fields.items():
                setattr(row, k, val)
    for rid, row in db_relations.items():
        if rid not in graph.relations and row.deleted_at is None:
            row.deleted_at = _now()

    db_views = {v.slug: v for v in db.scalars(select(View).where(View.tenant_id == tenant_id)).all()}
    for vid, view in graph.views.items():
        row = db_views.get(vid)
        fields = dict(
            name=view.name,
            lang=view.lang,
            viewpoint=view.viewpoint,
            include=view.include.model_dump(),
        )
        if row is None:
            db.add(View(tenant_id=tenant_id, slug=vid, status="draft", **fields))
        else:
            for k, val in fields.items():
                setattr(row, k, val)

    db.flush()

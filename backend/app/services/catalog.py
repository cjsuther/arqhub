"""Element and relationship operations (SPEC §7 catalog).

Every mutation goes through the DSL engine (build a patch -> apply -> sync) so it
inherits the same validation and audit path as a DSL import. Routers stay thin.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from ..core.auth import Principal
from ..core.deps import write_audit
from ..schemas.api import (
    ElementCreate,
    ElementRead,
    ElementUpdate,
    RelationshipCreate,
    RelationshipRead,
)
from .dsl import ModelGraph, apply_document
from .dsl.graph import Element as GraphElement
from .dsl.graph import Relation as GraphRelation
from .dsl.schema import DslDocument, ElementDef, PatchSection, RelationDef
from .repository import load_graph, sync_graph


def _element_read(el: GraphElement) -> ElementRead:
    return ElementRead(
        slug=el.slug,
        name=el.name,
        kind=el.kind,
        domain=el.domain,
        owner=el.owner,
        description=el.description,
        lifecycle=el.lifecycle.value,
        tags=list(el.tags),
        properties=dict(el.properties),
        mappings=dict(el.mappings),
    )


def _relation_read(rel: GraphRelation) -> RelationshipRead:
    return RelationshipRead.model_validate(
        {
            "slug": rel.id,
            "from": rel.from_,
            "to": rel.to,
            "kind": rel.kind,
            "label": rel.label,
            "properties": dict(rel.properties),
        }
    )


def _apply(db, principal: Principal, patch: PatchSection, *, action: str, entity: str, entity_id: str) -> ModelGraph:
    graph = load_graph(db, principal.tenant_id)
    result = apply_document(graph, DslDocument(patch=patch))
    if not result.validation.ok:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": [i.model_dump() for i in result.validation.errors]},
        )
    sync_graph(db, principal.tenant_id, result.graph)
    write_audit(db, principal, action=action, entity=entity, entity_id=entity_id)
    db.commit()
    return result.graph


# --- Elements ----------------------------------------------------------------
def list_elements(db, tenant_id: str, *, kind=None, domain=None, lifecycle=None, tag=None, q=None):
    graph = load_graph(db, tenant_id)
    out = []
    for el in graph.elements.values():
        if kind and el.kind != kind:
            continue
        if domain and el.domain != domain:
            continue
        if lifecycle and el.lifecycle.value != lifecycle:
            continue
        if tag and tag not in el.tags:
            continue
        if q and q.lower() not in f"{el.slug} {el.name} {el.description or ''}".lower():
            continue
        out.append(_element_read(el))
    return out


def get_element(db, tenant_id: str, slug: str) -> ElementRead:
    graph = load_graph(db, tenant_id)
    el = graph.elements.get(slug)
    if el is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Element '{slug}' not found.")
    return _element_read(el)


def create_element(db, principal: Principal, payload: ElementCreate) -> ElementRead:
    graph = load_graph(db, principal.tenant_id)
    if payload.slug in graph.elements:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Element '{payload.slug}' already exists.")
    definition = ElementDef(**payload.model_dump(exclude={"slug"}))
    graph = _apply(
        db, principal, PatchSection(add_elements={payload.slug: definition}),
        action="create", entity="element", entity_id=payload.slug,
    )
    return _element_read(graph.elements[payload.slug])


def update_element(db, principal: Principal, slug: str, payload: ElementUpdate) -> ElementRead:
    graph = load_graph(db, principal.tenant_id)
    if slug not in graph.elements:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Element '{slug}' not found.")
    changes = payload.model_dump(exclude_none=True)
    graph = _apply(
        db, principal, PatchSection(update_elements={slug: changes}),
        action="update", entity="element", entity_id=slug,
    )
    return _element_read(graph.elements[slug])


def delete_element(db, principal: Principal, slug: str) -> None:
    graph = load_graph(db, principal.tenant_id)
    if slug not in graph.elements:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Element '{slug}' not found.")
    _apply(
        db, principal, PatchSection(remove_elements=[slug]),
        action="delete", entity="element", entity_id=slug,
    )


# --- Relationships -----------------------------------------------------------
def list_relationships(db, tenant_id: str):
    graph = load_graph(db, tenant_id)
    return [_relation_read(r) for r in graph.relations.values()]


def create_relationship(db, principal: Principal, payload: RelationshipCreate) -> RelationshipRead:
    definition = RelationDef.model_validate(
        {
            "id": payload.slug,
            "from": payload.from_,
            "to": payload.to,
            "kind": payload.kind,
            "label": payload.label,
            "properties": payload.properties,
        }
    )
    graph = load_graph(db, principal.tenant_id)
    result = apply_document(graph, DslDocument(patch=PatchSection(add_relations=[definition])))
    if not result.validation.ok:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"errors": [i.model_dump() for i in result.validation.errors]},
        )
    # Find the id the engine assigned (explicit slug or deterministic).
    new_ids = set(result.graph.relations) - set(graph.relations)
    rid = payload.slug or (next(iter(new_ids)) if new_ids else None)
    sync_graph(db, principal.tenant_id, result.graph)
    write_audit(db, principal, action="create", entity="relationship", entity_id=rid)
    db.commit()
    return _relation_read(result.graph.relations[rid])


def delete_relationship(db, principal: Principal, slug: str) -> None:
    graph = load_graph(db, principal.tenant_id)
    if slug not in graph.relations:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Relationship '{slug}' not found.")
    _apply(
        db, principal, PatchSection(remove_relations=[slug]),
        action="delete", entity="relationship", entity_id=slug,
    )

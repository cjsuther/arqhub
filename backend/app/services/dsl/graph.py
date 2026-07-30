"""In-memory canonical model graph.

``ModelGraph`` is the DB-agnostic representation the DSL engine operates on:
the importer merges DSL documents into it, the exporter serialises it back, the
diff compares two of them. Persistence maps rows <-> ``ModelGraph`` elsewhere,
so the whole DSL layer stays unit-testable without a database.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field

from .registry import normalize_relation
from .schema import ElementDef, RelationDef, ViewDef

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    return _SLUG_RE.sub("-", text.strip().lower()).strip("-")


def relation_id(from_: str, kind: str, to: str) -> str:
    """Deterministic id for a relation that did not declare one."""
    return f"r-{from_}-{normalize_relation(kind)}-{to}"


class Element(ElementDef):
    """An element inside the graph; carries its own slug (the map key)."""

    slug: str


class Relation(RelationDef):
    """A relation with a guaranteed id and normalised (alias-free) kind."""

    id: str


class ModelGraph(BaseModel):
    elements: dict[str, Element] = Field(default_factory=dict)
    relations: dict[str, Relation] = Field(default_factory=dict)
    views: dict[str, ViewDef] = Field(default_factory=dict)

    def add_element(self, slug: str, definition: ElementDef) -> Element:
        el = Element(slug=slug, **definition.model_dump())
        self.elements[slug] = el
        return el

    def add_relation(self, definition: RelationDef) -> Relation:
        kind = normalize_relation(definition.kind)
        rid = definition.id or relation_id(definition.from_, kind, definition.to)
        data = definition.model_dump(by_alias=True)
        data.update(id=rid, kind=kind)
        rel = Relation.model_validate(data)
        self.relations[rid] = rel
        return rel

    def add_view(self, view: ViewDef) -> ViewDef:
        self.views[view.id] = view
        return view

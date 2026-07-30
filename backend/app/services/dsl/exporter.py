"""Serialise a ModelGraph back to DSL YAML (SPEC §5).

Emits canonical form: default/empty fields are omitted to keep the YAML lean,
and relation kinds are the canonical tokens (aliases like ``uses`` are resolved
on import). Roundtrip is guaranteed semantically: ``load(export(g)) == g``.
"""

from __future__ import annotations

import yaml

from .graph import ModelGraph
from .registry import Lifecycle
from .schema import DSL_VERSION, ViewDef


def _element_dict(el) -> dict:
    out: dict = {"name": el.name, "kind": el.kind}
    if el.domain:
        out["domain"] = el.domain
    if el.owner:
        out["owner"] = el.owner
    if el.description:
        out["description"] = el.description
    if el.lifecycle != Lifecycle.active:
        out["lifecycle"] = el.lifecycle.value
    if el.tags:
        out["tags"] = list(el.tags)
    if el.properties:
        out["properties"] = dict(el.properties)
    if el.mappings:
        out["mappings"] = dict(el.mappings)
    return out


def _relation_dict(rel) -> dict:
    out: dict = {"id": rel.id, "from": rel.from_, "to": rel.to, "kind": rel.kind}
    if rel.label:
        out["label"] = rel.label
    if rel.properties:
        out["properties"] = dict(rel.properties)
    return out


def _view_dict(view: ViewDef) -> dict:
    out: dict = {"id": view.id, "name": view.name, "lang": view.lang}
    if view.viewpoint:
        out["viewpoint"] = view.viewpoint
    include: dict = {}
    if view.include.elements:
        include["elements"] = list(view.include.elements)
    include["relations"] = view.include.relations
    out["include"] = include
    return out


def graph_to_dict(graph: ModelGraph) -> dict:
    doc: dict = {"dsl": DSL_VERSION}
    model: dict = {}
    if graph.elements:
        model["elements"] = {slug: _element_dict(el) for slug, el in graph.elements.items()}
    if graph.relations:
        model["relations"] = [_relation_dict(rel) for rel in graph.relations.values()]
    if model:
        doc["model"] = model
    if graph.views:
        doc["views"] = [_view_dict(v) for v in graph.views.values()]
    return doc


def export_dsl(graph: ModelGraph) -> str:
    return yaml.safe_dump(
        graph_to_dict(graph),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )

"""Apply a DSL document (full model or patch) to a ModelGraph (SPEC §5.3).

The importer is pure: it takes an input graph, returns a new graph plus a
structured report (validation + semantic diff). The API layer decides whether to
persist based on ``report.ok`` and the ``dry_run`` flag.
"""

from __future__ import annotations

import copy

from pydantic import BaseModel

from .diff import ModelDiff, diff_graphs
from .graph import Element, ModelGraph, Relation
from .schema import DslDocument
from .validator import ValidationReport, validate_graph


class ImportResult(BaseModel):
    graph: ModelGraph
    validation: ValidationReport
    diff: ModelDiff


def _apply_model(graph: ModelGraph, doc: DslDocument, replace: bool) -> None:
    if doc.model is None:
        return
    if replace:
        graph.elements.clear()
        graph.relations.clear()
    for slug, definition in doc.model.elements.items():
        graph.add_element(slug, definition)
    for relation in doc.model.relations:
        graph.add_relation(relation)


def _apply_views(graph: ModelGraph, doc: DslDocument) -> None:
    for view in doc.views or []:
        graph.add_view(view)


def _apply_patch(graph: ModelGraph, doc: DslDocument) -> None:
    patch = doc.patch
    if patch is None:
        return

    for slug, definition in patch.add_elements.items():
        graph.add_element(slug, definition)
    for relation in patch.add_relations:
        graph.add_relation(relation)

    for slug, changes in patch.update_elements.items():
        existing = graph.elements.get(slug)
        if existing is not None:
            # Re-validate (not model_copy) so partial updates coerce types,
            # e.g. a raw "deprecated" string back into the Lifecycle enum.
            merged = {**existing.model_dump(), **changes}
            graph.elements[slug] = Element.model_validate(merged)

    for rid, changes in patch.update_relations.items():
        existing = graph.relations.get(rid)
        if existing is not None:
            merged = {**existing.model_dump(by_alias=True), **changes}
            graph.relations[rid] = Relation.model_validate(merged)

    for rid in patch.remove_relations:
        graph.relations.pop(rid, None)

    for slug in patch.remove_elements:
        graph.elements.pop(slug, None)
        # Drop relations left dangling by the removal.
        for rid in [r.id for r in graph.relations.values() if slug in (r.from_, r.to)]:
            graph.relations.pop(rid, None)


def apply_document(
    graph: ModelGraph | None,
    doc: DslDocument,
    *,
    replace: bool = False,
) -> ImportResult:
    """Apply ``doc`` to a copy of ``graph`` and report validation + diff."""
    before = copy.deepcopy(graph) if graph is not None else ModelGraph()
    after = copy.deepcopy(before)

    _apply_model(after, doc, replace=replace)
    _apply_patch(after, doc)
    _apply_views(after, doc)

    return ImportResult(
        graph=after,
        validation=validate_graph(after),
        diff=diff_graphs(before, after),
    )

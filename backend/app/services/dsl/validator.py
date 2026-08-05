"""Semantic validation of a ModelGraph against the registry (SPEC §4.2 / §5.3).

Returns a structured report (errors + warnings) rather than raising, so an LLM
can read it and self-correct. Hard violations are errors; the relation matrix
mismatches are warnings — per spec, "return warnings, don't block except hard
violations".
"""

from __future__ import annotations

from pydantic import BaseModel

from .graph import ModelGraph
from .registry import (
    VALID_RELATIONS,
    Lang,
    is_valid_kind,
    kind_exists_in,
    normalize_relation,
    relation_exists_in,
)


class Issue(BaseModel):
    code: str
    message: str
    path: str  # dotted locator, e.g. "elements.api-pagos" or "views.v1"


class ValidationReport(BaseModel):
    errors: list[Issue] = []
    warnings: list[Issue] = []

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_graph(graph: ModelGraph) -> ValidationReport:
    report = ValidationReport()

    for slug, el in graph.elements.items():
        if not is_valid_kind(el.kind):
            report.errors.append(
                Issue(
                    code="unknown_kind",
                    message=f"Unknown element kind '{el.kind}'.",
                    path=f"elements.{slug}",
                )
            )

    for rid, rel in graph.relations.items():
        kind = normalize_relation(rel.kind)
        path = f"relations.{rid}"
        if kind not in VALID_RELATIONS:
            report.errors.append(
                Issue(code="unknown_relation", message=f"Unknown relation kind '{rel.kind}'.", path=path)
            )
        if rel.from_ not in graph.elements:
            report.errors.append(
                Issue(code="dangling_from", message=f"Relation source '{rel.from_}' does not exist.", path=path)
            )
        if rel.to not in graph.elements:
            report.errors.append(
                Issue(code="dangling_to", message=f"Relation target '{rel.to}' does not exist.", path=path)
            )

    for vid, view in graph.views.items():
        path = f"views.{vid}"
        try:
            lang = Lang(view.lang)
        except ValueError:
            report.errors.append(
                Issue(code="unknown_lang", message=f"Unknown view language '{view.lang}'.", path=path)
            )
            continue

        for el_slug in view.include.elements:
            el = graph.elements.get(el_slug)
            if el is None:
                report.errors.append(
                    Issue(code="view_missing_element", message=f"View references unknown element '{el_slug}'.", path=path)
                )
            elif not kind_exists_in(el.kind, lang):
                report.warnings.append(
                    Issue(
                        code="kind_not_in_lang",
                        message=f"El elemento '{el_slug}' (tipo '{el.kind}') no tiene representación en {lang.value}.",
                        path=path,
                    )
                )

        if isinstance(view.include.relations, list):
            for rid in view.include.relations:
                rel = graph.relations.get(rid)
                if rel is None:
                    report.errors.append(
                        Issue(code="view_missing_relation", message=f"View references unknown relation '{rid}'.", path=path)
                    )
                elif not relation_exists_in(rel.kind, lang):
                    report.warnings.append(
                        Issue(
                            code="relation_not_in_lang",
                            message=f"La relación '{rid}' (tipo '{rel.kind}') no tiene representación en {lang.value}.",
                            path=path,
                        )
                    )

    return report

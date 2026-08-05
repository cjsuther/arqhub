"""Deterministic model-analysis rules (SPEC §10).

Pure over ``ModelGraph`` so it is unit-testable and reusable by both the UI
("Analizar modelo") and MCP (``propose_optimization``). Output is structured for
an LLM to consume and propose the corresponding patch.
"""

from __future__ import annotations

from collections import defaultdict
from difflib import SequenceMatcher
from itertools import combinations

from pydantic import BaseModel

from .dsl.graph import ModelGraph
from .dsl.validator import validate_graph

NAME_SIMILARITY_THRESHOLD = 0.85

# User-facing lifecycle labels (Spanish UI).
_LIFECYCLE_ES = {"proposed": "propuesto", "active": "activo", "deprecated": "obsoleto", "retired": "retirado"}


class Finding(BaseModel):
    code: str
    severity: str  # info | warning | error
    message: str
    entities: list[str]
    suggestion: str | None = None


def _duplicates(graph: ModelGraph) -> list[Finding]:
    out: list[Finding] = []
    for a, b in combinations(graph.elements.values(), 2):
        if a.kind != b.kind:
            continue
        ratio = SequenceMatcher(None, a.name.lower(), b.name.lower()).ratio()
        if ratio >= NAME_SIMILARITY_THRESHOLD:
            out.append(Finding(
                code="possible_duplicate", severity="warning",
                message=f"'{a.name}' y '{b.name}' ({a.kind}) parecen duplicados (similitud {ratio:.2f}).",
                entities=[a.slug, b.slug],
                suggestion="Fusioná uno en el otro y reapuntá las relaciones.",
            ))
    return out


def _orphans(graph: ModelGraph) -> list[Finding]:
    related = set()
    for r in graph.relations.values():
        related.add(r.from_)
        related.add(r.to)
    in_views = set()
    for v in graph.views.values():
        in_views.update(v.include.elements)

    out: list[Finding] = []
    for slug, el in graph.elements.items():
        if slug not in related:
            out.append(Finding(
                code="orphan_no_relations", severity="info",
                message=f"'{el.name}' no tiene relaciones.", entities=[slug],
                suggestion="Relacionalo con el modelo o eliminalo.",
            ))
        if slug not in in_views:
            out.append(Finding(
                code="orphan_no_views", severity="info",
                message=f"'{el.name}' no aparece en ninguna vista.", entities=[slug],
            ))
    return out


def _lifecycle(graph: ModelGraph) -> list[Finding]:
    out: list[Finding] = []
    for r in graph.relations.values():
        src, dst = graph.elements.get(r.from_), graph.elements.get(r.to)
        if not src or not dst:
            continue
        if src.lifecycle.value == "active" and dst.lifecycle.value in ("deprecated", "retired"):
            out.append(Finding(
                code="lifecycle_inconsistency", severity="warning",
                message=f"'{src.name}' (activo) depende de '{dst.name}' ({_LIFECYCLE_ES.get(dst.lifecycle.value, dst.lifecycle.value)}).",
                entities=[r.from_, r.to],
                suggestion="Migrá fuera del elemento obsoleto o actualizá su ciclo de vida.",
            ))
    return out


def _coupling(graph: ModelGraph) -> list[Finding]:
    degree: dict[str, int] = defaultdict(int)
    for r in graph.relations.values():
        degree[r.from_] += 1
        degree[r.to] += 1
    if not degree:
        return []
    values = sorted(degree.values())
    p90 = values[int(0.9 * (len(values) - 1))]
    threshold = max(4, p90)
    out: list[Finding] = []
    for slug, deg in degree.items():
        if deg >= threshold and deg > 3:
            el = graph.elements.get(slug)
            out.append(Finding(
                code="high_coupling", severity="info",
                message=f"'{el.name if el else slug}' tiene grado {deg} (>= p90 {threshold}).",
                entities=[slug],
                suggestion="Considerá descomponerlo o introducir un intermediario.",
            ))
    return out


def _matrix(graph: ModelGraph) -> list[Finding]:
    report = validate_graph(graph)
    out: list[Finding] = []
    for issue in report.warnings:
        if issue.code in ("relation_not_in_lang", "kind_not_in_lang"):
            out.append(Finding(
                code="matrix_warning", severity="warning", message=issue.message, entities=[issue.path],
            ))
    return out


def analyze(graph: ModelGraph) -> list[Finding]:
    findings: list[Finding] = []
    for rule in (_duplicates, _orphans, _lifecycle, _coupling, _matrix):
        findings.extend(rule(graph))
    order = {"error": 0, "warning": 1, "info": 2}
    findings.sort(key=lambda f: order.get(f.severity, 3))
    return findings

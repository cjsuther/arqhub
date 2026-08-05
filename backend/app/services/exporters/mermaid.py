"""Mermaid export of a view (SPEC §7). Compact, text-first — ideal for an LLM
(via MCP) to grasp a diagram quickly, and renders in Markdown viewers.

Business/behaviour relations become a ``flowchart``; the goal is legibility, not
notation fidelity (that's what the ArchiMate/BPMN/XMI exporters are for).
"""

from __future__ import annotations

import re

from ..dsl.graph import Element, Relation
from ..dsl.schema import ViewDef

# Relation → Mermaid arrow (approximate the semantics for readability).
_ARROW = {
    "composition": "--o",
    "aggregation": "--o",
    "assignment": "-->",
    "realization": "-.->",
    "serving": "-->",
    "access": "-.->",
    "triggering": "==>",
    "sequence-flow": "==>",
    "message-flow": "-.->",
    "association": "---",
    "specialization": "-.->",
}


def _nid(slug: str) -> str:
    return "n_" + re.sub(r"[^a-zA-Z0-9_]", "_", slug)


def _label(text: str) -> str:
    # Mermaid labels are quoted; neutralise quotes and pipes.
    return text.replace('"', "'").replace("|", "/")


def export_mermaid(els: list[Element], rels: list[Relation], view: ViewDef) -> str:
    lines = [f"%% {view.name} ({view.lang})", "flowchart TD"]
    for e in els:
        lines.append(f'  {_nid(e.slug)}["{_label(e.name)}<br/><small>{_label(e.kind)}</small>"]')
    for r in rels:
        arrow = _ARROW.get(r.kind, "-->")
        label = _label(r.label) if r.label else _label(r.kind)
        lines.append(f"  {_nid(r.from_)} {arrow}|{label}| {_nid(r.to)}")
    return "\n".join(lines) + "\n"

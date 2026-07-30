"""Server-side SVG rendering of a view (SPEC §7 /views/{slug}/render).

A deterministic grid layout coloured by ArchiMate layer — enough for thumbnails
and Teams cards. The rich, ELK-laid-out canvas lives in the frontend; this is the
headless fallback and never depends on a browser.
"""

from __future__ import annotations

import html
import math

from ..dsl import ModelGraph
from ..dsl.registry import KIND_LAYER

# Layer palette, aligned with the frontend design system (SPEC §8.2).
LAYER_FILL = {
    "business": "#f7dd8f",
    "application": "#a9d1f0",
    "technology": "#a9dfa9",
    "motivation": "#cdb8ef",
}
LAYER_STROKE = {
    "business": "#c9a227",
    "application": "#3a7fc4",
    "technology": "#3d9a3d",
    "motivation": "#8a63c9",
}

BOX_W, BOX_H, GAP_X, GAP_Y, MARGIN = 170, 64, 60, 60, 32


def _subgraph_elements(graph: ModelGraph, view) -> list:
    return [graph.elements[s] for s in view.include.elements if s in graph.elements]


def _view_edges(graph: ModelGraph, view) -> list:
    included = set(view.include.elements)
    edges = []
    for rel in graph.relations.values():
        if isinstance(view.include.relations, list):
            if rel.id not in view.include.relations:
                continue
        elif not (rel.from_ in included and rel.to in included):
            continue
        edges.append(rel)
    return edges


def render_view_svg(graph: ModelGraph, view) -> str:
    elements = _subgraph_elements(graph, view)
    edges = _view_edges(graph, view)

    cols = max(1, math.ceil(math.sqrt(len(elements)))) if elements else 1
    pos: dict[str, tuple[float, float]] = {}
    for i, el in enumerate(elements):
        row, col = divmod(i, cols)
        x = MARGIN + col * (BOX_W + GAP_X)
        y = MARGIN + row * (BOX_H + GAP_Y)
        pos[el.slug] = (x, y)

    rows = math.ceil(len(elements) / cols) if elements else 1
    width = MARGIN * 2 + cols * BOX_W + (cols - 1) * GAP_X
    height = MARGIN * 2 + rows * BOX_H + (rows - 1) * GAP_Y

    parts: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Inter, system-ui, sans-serif">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" '
        'orient="auto" markerUnits="strokeUnits">'
        '<path d="M0,0 L8,3 L0,6 Z" fill="#64748b"/></marker></defs>',
        f'<rect width="{width}" height="{height}" fill="white"/>',
    ]

    for rel in edges:
        if rel.from_ not in pos or rel.to not in pos:
            continue
        x1, y1 = pos[rel.from_]
        x2, y2 = pos[rel.to]
        cx1, cy1 = x1 + BOX_W / 2, y1 + BOX_H / 2
        cx2, cy2 = x2 + BOX_W / 2, y2 + BOX_H / 2
        parts.append(
            f'<line x1="{cx1:.0f}" y1="{cy1:.0f}" x2="{cx2:.0f}" y2="{cy2:.0f}" '
            'stroke="#64748b" stroke-width="1.5" marker-end="url(#arrow)"/>'
        )

    for el in elements:
        x, y = pos[el.slug]
        layer = KIND_LAYER.get(el.kind, "application")
        fill, stroke = LAYER_FILL[layer], LAYER_STROKE[layer]
        name = html.escape(el.name if len(el.name) <= 22 else el.name[:21] + "…")
        parts.append(
            f'<g><rect x="{x}" y="{y}" width="{BOX_W}" height="{BOX_H}" rx="6" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
            f'<text x="{x + 10}" y="{y + 26}" font-size="13" font-weight="600" fill="#1e293b">{name}</text>'
            f'<text x="{x + 10}" y="{y + 46}" font-size="10" fill="#475569">{html.escape(el.kind)}</text></g>'
        )

    parts.append("</svg>")
    return "".join(parts)

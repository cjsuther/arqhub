"""Server-side SVG rendering of a view (SPEC §7 /views/{slug}/render).

Mirrors the canvas: uses the saved layout (positions, sizes, pool nesting) so the
thumbnail matches what the user arranged. Falls back to a deterministic grid when
a view has no saved layout yet. Used for view thumbnails and Teams cards.
"""

from __future__ import annotations

import html
import math

from ..dsl import ModelGraph
from ..dsl.registry import KIND_LAYER

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


def _svg_header(width: float, height: float) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" height="{height:.0f}" '
        f'viewBox="0 0 {width:.0f} {height:.0f}" font-family="Inter, system-ui, sans-serif">',
        '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" '
        'orient="auto" markerUnits="strokeUnits"><path d="M0,0 L8,3 L0,6 Z" fill="#64748b"/></marker></defs>',
        f'<rect width="{width:.0f}" height="{height:.0f}" fill="white"/>',
    ]


def _box(el, x: float, y: float, w: float, h: float) -> str:
    layer = KIND_LAYER.get(el.kind, "application")
    fill, stroke = LAYER_FILL[layer], LAYER_STROKE[layer]
    name = html.escape(el.name if len(el.name) <= 24 else el.name[:23] + "…")
    return (
        f'<g><rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="6" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'
        f'<text x="{x + 10:.0f}" y="{y + 24:.0f}" font-size="13" font-weight="600" fill="#1e293b">{name}</text>'
        f'<text x="{x + 10:.0f}" y="{y + 42:.0f}" font-size="10" fill="#475569">{html.escape(el.kind)}</text></g>'
    )


def _pool(el, x: float, y: float, w: float, h: float) -> str:
    name = html.escape(el.name if len(el.name) <= 30 else el.name[:29] + "…")
    return (
        f'<g><rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" rx="6" '
        f'fill="rgba(99,102,241,.06)" stroke="#94a3b8" stroke-width="1.5"/>'
        f'<rect x="{x:.0f}" y="{y:.0f}" width="30" height="{h:.0f}" fill="rgba(99,102,241,.12)" stroke="#94a3b8" stroke-width="1"/>'
        f'<text x="{x + 20:.0f}" y="{y + h / 2:.0f}" font-size="12" font-weight="600" fill="#475569" '
        f'text-anchor="middle" transform="rotate(-90 {x + 20:.0f} {y + h / 2:.0f})">{name}</text></g>'
    )


def _grid_svg(elements: list, edges: list) -> str:
    """Fallback: grid layout when no saved layout exists."""
    cols = max(1, math.ceil(math.sqrt(len(elements)))) if elements else 1
    pos = {}
    for i, el in enumerate(elements):
        row, col = divmod(i, cols)
        pos[el.slug] = (MARGIN + col * (BOX_W + GAP_X), MARGIN + row * (BOX_H + GAP_Y))
    rows = math.ceil(len(elements) / cols) if elements else 1
    width = MARGIN * 2 + cols * BOX_W + (cols - 1) * GAP_X
    height = MARGIN * 2 + rows * BOX_H + (rows - 1) * GAP_Y
    parts = _svg_header(width, height)
    for rel in edges:
        if rel.from_ in pos and rel.to in pos:
            x1, y1 = pos[rel.from_]
            x2, y2 = pos[rel.to]
            parts.append(
                f'<line x1="{x1 + BOX_W / 2:.0f}" y1="{y1 + BOX_H / 2:.0f}" '
                f'x2="{x2 + BOX_W / 2:.0f}" y2="{y2 + BOX_H / 2:.0f}" '
                'stroke="#64748b" stroke-width="1.5" marker-end="url(#arrow)"/>'
            )
    for el in elements:
        x, y = pos[el.slug]
        parts.append(_box(el, x, y, BOX_W, BOX_H))
    parts.append("</svg>")
    return "".join(parts)


def render_view_svg(graph: ModelGraph, view, layout: dict | None = None) -> str:
    elements = _subgraph_elements(graph, view)
    edges = _view_edges(graph, view)
    layout = layout or {}
    if not layout:
        return _grid_svg(elements, edges)

    pool_slugs = {l.get("parent") for l in layout.values() if l.get("parent")}
    # child -> parent, to hide the containment/membership edge shown by nesting.
    nested_parent = {slug: l.get("parent") for slug, l in layout.items() if l.get("parent")}

    # Absolute rects: pools at their own coords, members offset by their pool.
    rect: dict[str, tuple[float, float, float, float]] = {}
    for el in elements:
        if el.slug in pool_slugs and el.slug in layout:
            l = layout[el.slug]
            rect[el.slug] = (l["x"], l["y"], l.get("w") or 320, l.get("h") or 120)
    for el in elements:
        if el.slug in pool_slugs or el.slug not in layout:
            continue
        l = layout[el.slug]
        w, h = l.get("w") or BOX_W, l.get("h") or BOX_H
        parent = l.get("parent")
        if parent and parent in rect:
            px, py, _, _ = rect[parent]
            rect[el.slug] = (px + l["x"], py + l["y"], w, h)
        else:
            rect[el.slug] = (l["x"], l["y"], w, h)

    # Elements with no saved position: drop into a row below everything.
    missing = [e for e in elements if e.slug not in rect]
    if missing:
        base_y = (max((y + h for _, y, _, h in rect.values()), default=0)) + GAP_Y
        for i, e in enumerate(missing):
            rect[e.slug] = (MARGIN + i * (BOX_W + GAP_X), base_y, BOX_W, BOX_H)

    xs = [x for x, _, w, _ in rect.values()] + [x + w for x, _, w, _ in rect.values()]
    ys = [y for _, y, _, h in rect.values()] + [y + h for _, y, _, h in rect.values()]
    min_x, min_y = min(xs, default=0), min(ys, default=0)
    dx, dy = MARGIN - min_x, MARGIN - min_y
    width = (max(xs, default=0) - min_x) + MARGIN * 2
    height = (max(ys, default=0) - min_y) + MARGIN * 2

    parts = _svg_header(width, height)

    # Pools first (behind), then edges, then boxes.
    for el in elements:
        if el.slug in pool_slugs and el.slug in rect:
            x, y, w, h = rect[el.slug]
            parts.append(_pool(el, x + dx, y + dy, w, h))

    nestable = {"composition", "aggregation", "assignment"}
    for rel in edges:
        # A containment/membership relation drawn as nesting gets no edge.
        if rel.kind in nestable and nested_parent.get(rel.to) == rel.from_:
            continue
        if rel.from_ not in rect or rel.to not in rect:
            continue
        x1, y1, w1, h1 = rect[rel.from_]
        x2, y2, w2, h2 = rect[rel.to]
        parts.append(
            f'<line x1="{x1 + w1 / 2 + dx:.0f}" y1="{y1 + h1 / 2 + dy:.0f}" '
            f'x2="{x2 + w2 / 2 + dx:.0f}" y2="{y2 + h2 / 2 + dy:.0f}" '
            'stroke="#64748b" stroke-width="1.5" marker-end="url(#arrow)"/>'
        )

    for el in elements:
        if el.slug in pool_slugs:
            continue
        x, y, w, h = rect[el.slug]
        parts.append(_box(el, x + dx, y + dy, w, h))

    parts.append("</svg>")
    return "".join(parts)

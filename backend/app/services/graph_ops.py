"""Graph queries over the model: impact analysis and element->views (SPEC §7)."""

from __future__ import annotations

from collections import deque

from fastapi import HTTPException, status
from pydantic import BaseModel

from .dsl import ModelGraph
from .repository import load_graph


class ImpactNode(BaseModel):
    slug: str
    name: str
    kind: str
    lifecycle: str
    depth: int


class ImpactEdge(BaseModel):
    from_: str
    to: str
    kind: str


class ImpactResult(BaseModel):
    root: str
    depth: int
    nodes: list[ImpactNode]
    edges: list[ImpactEdge]


def _adjacency(graph: ModelGraph, directed: bool) -> dict[str, list[tuple[str, str]]]:
    adj: dict[str, list[tuple[str, str]]] = {slug: [] for slug in graph.elements}
    for rel in graph.relations.values():
        adj.setdefault(rel.from_, []).append((rel.to, rel.id))
        if not directed:
            adj.setdefault(rel.to, []).append((rel.from_, rel.id))
    return adj


def impact(db, tenant_id: str, slug: str, *, depth: int = 2, directed: bool = True) -> ImpactResult:
    """BFS from ``slug`` up to ``depth`` hops over the relation graph (SPEC §7)."""
    graph = load_graph(db, tenant_id)
    if slug not in graph.elements:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Element '{slug}' not found.")

    adj = _adjacency(graph, directed)
    seen = {slug: 0}
    edge_ids: set[str] = set()
    queue: deque[str] = deque([slug])
    while queue:
        cur = queue.popleft()
        if seen[cur] >= depth:
            continue
        for neighbour, rid in adj.get(cur, []):
            edge_ids.add(rid)
            if neighbour not in seen:
                seen[neighbour] = seen[cur] + 1
                queue.append(neighbour)

    nodes = [
        ImpactNode(
            slug=s, name=graph.elements[s].name, kind=graph.elements[s].kind,
            lifecycle=graph.elements[s].lifecycle.value, depth=d,
        )
        for s, d in sorted(seen.items(), key=lambda kv: (kv[1], kv[0]))
        if s in graph.elements
    ]
    edges = [
        ImpactEdge(from_=graph.relations[e].from_, to=graph.relations[e].to, kind=graph.relations[e].kind)
        for e in sorted(edge_ids)
        if graph.relations[e].from_ in seen and graph.relations[e].to in seen
    ]
    return ImpactResult(root=slug, depth=depth, nodes=nodes, edges=edges)


def element_views(db, tenant_id: str, slug: str) -> list[dict]:
    """Views where the element appears — the navigation index (SPEC §1, §7)."""
    graph = load_graph(db, tenant_id)
    if slug not in graph.elements:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Element '{slug}' not found.")
    return [
        {"slug": v.id, "name": v.name, "lang": v.lang}
        for v in graph.views.values()
        if slug in v.include.elements
    ]

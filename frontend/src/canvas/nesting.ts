// Nested notation (ArchiMate §): a containment relation (composition, aggregation,
// assignment) can be shown by placing the child element *inside* the parent instead
// of drawing a connector. Nesting is presentation (persisted as layout.parent); the
// relation stays in the model and its edge is hidden while nested.
import type { Registry, ViewGraph } from "../lib/types";
import type { ArchiNode } from "./ArchiMateNode";

export const NESTABLE = new Set(["composition", "aggregation", "assignment"]);
export const NEST_HEADER = 28;
export const NEST_PAD = 14;
const CHILD_W = 184;
const CHILD_H = 66;

// child slug -> parent slug, from saved layout.parent, keeping only pairs that still
// have a nestable relation (parent = the relation's source) and are single-level.
export function nestingFromLayout(vg: ViewGraph): Record<string, string> {
  const pairs = new Set(
    vg.relations.filter((r) => NESTABLE.has(r.kind)).map((r) => `${r.from}>${r.to}`),
  );
  const map: Record<string, string> = {};
  for (const l of vg.layout) {
    if (l.parent && pairs.has(`${l.parent}>${l.element}`)) map[l.element] = l.parent;
  }
  // Drop grandchildren (single-level nesting only).
  for (const child of Object.keys(map)) {
    if (map[map[child]]) delete map[child];
  }
  return map;
}

// Which parents a node may be nested into (nestable relation source -> node).
export function validParents(vg: ViewGraph, childSlug: string): Set<string> {
  const out = new Set<string>();
  for (const r of vg.relations) {
    if (NESTABLE.has(r.kind) && r.to === childSlug) out.add(r.from);
  }
  return out;
}

function archiData(reg: Registry, vg: ViewGraph, e: ViewGraph["elements"][number], style: unknown) {
  return {
    element: e,
    layer: reg.kinds[e.kind]?.layer ?? "application",
    lang: vg.view.lang,
    projection: reg.kinds[e.kind]?.mappings[vg.view.lang] ?? null,
    style: style as { borderColor?: string; background?: string } | undefined,
  };
}

// Build React Flow nodes with containers for the nested pairs. `positions` are
// absolute for top-level nodes and relative for nested children.
export function nestNodes(
  vg: ViewGraph,
  reg: Registry,
  positions: Record<string, { x: number; y: number }>,
  styleMap: Record<string, { borderColor?: string; background?: string }>,
  parentMap: Record<string, string>,
): ArchiNode[] {
  const childrenOf: Record<string, ViewGraph["elements"]> = {};
  for (const e of vg.elements) {
    const p = parentMap[e.slug];
    if (p) (childrenOf[p] ??= []).push(e);
  }
  const parents = new Set(Object.keys(childrenOf));

  const size: Record<string, { w: number; h: number }> = {};
  for (const [p, kids] of Object.entries(childrenOf)) {
    let maxX = 0;
    let maxY = 0;
    for (const k of kids) {
      const pos = positions[k.slug] ?? { x: NEST_PAD, y: NEST_HEADER };
      maxX = Math.max(maxX, pos.x + CHILD_W);
      maxY = Math.max(maxY, pos.y + CHILD_H);
    }
    size[p] = { w: Math.max(240, maxX + NEST_PAD), h: Math.max(NEST_HEADER + CHILD_H + NEST_PAD, maxY + NEST_PAD) };
  }

  const nodes: ArchiNode[] = [];
  // Parents/top-level first (React Flow requires a parent before its children).
  for (const e of vg.elements) {
    if (parentMap[e.slug]) continue;
    const node = {
      id: e.slug,
      type: "archimate" as const,
      position: positions[e.slug] ?? { x: 0, y: 0 },
      data: { ...archiData(reg, vg, e, styleMap[e.slug]), container: parents.has(e.slug) },
    } as ArchiNode;
    if (parents.has(e.slug)) {
      node.width = size[e.slug].w;
      node.height = size[e.slug].h;
    }
    nodes.push(node);
  }
  for (const e of vg.elements) {
    const p = parentMap[e.slug];
    if (!p) continue;
    nodes.push({
      id: e.slug,
      type: "archimate",
      parentId: p,
      position: positions[e.slug] ?? { x: NEST_PAD, y: NEST_HEADER },
      data: archiData(reg, vg, e, styleMap[e.slug]),
    } as ArchiNode);
  }
  return nodes;
}

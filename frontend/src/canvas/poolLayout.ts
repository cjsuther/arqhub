// BPMN pools/lanes as containers (SPEC §8.2, §16). Members are nested via React
// Flow parentId. Membership = assignment relation (model-first) OR an explicit
// layout.parent (drag, presentation). Pools are stacked vertically as swimlanes.
import type { LayoutNode, Registry, ViewGraph } from "../lib/types";
import type { ArchiNode } from "./ArchiMateNode";
import { POOL_HEADER, type PoolNode } from "./PoolNode";

export type CanvasNode = ArchiNode | PoolNode;

const CHILD_W = 170;
const CHILD_H = 56;
const GAP_X = 28;
const PAD = 16;
const POOL_GAP = 26;

export function poolKind(reg: Registry, kind: string): "pool" | "lane" | null {
  const p = reg.kinds[kind]?.mappings.bpmn;
  if (p === "Participant") return "pool";
  if (p === "Lane") return "lane";
  return null;
}

export function hasPools(vg: ViewGraph, reg: Registry): boolean {
  return vg.elements.some((e) => poolKind(reg, e.kind));
}

function archiData(reg: Registry, e: ViewGraph["elements"][number], style?: LayoutNode["style"]) {
  return {
    element: e,
    layer: reg.kinds[e.kind]?.layer ?? "application",
    lang: "bpmn" as const,
    projection: reg.kinds[e.kind]?.mappings.bpmn ?? null,
    style: style as { borderColor?: string; background?: string } | undefined,
  };
}

export function buildPoolNodes(vg: ViewGraph, reg: Registry): CanvasNode[] {
  const saved = new Map<string, LayoutNode>(vg.layout.map((l) => [l.element, l]));
  const pools = vg.elements.filter((e) => poolKind(reg, e.kind));
  const poolSet = new Set(pools.map((p) => p.slug));

  // Model-first membership: pool --assignment--> member.
  const assignParent: Record<string, string> = {};
  for (const r of vg.relations) {
    if (r.kind === "assignment" && poolSet.has(r.from)) assignParent[r.to] = r.from;
  }

  // Membership is defined by the assignment relation (model-first). Dragging a
  // node into/out of a pool edits that relation, so it stays the single source
  // of truth; layout.parent is only used below to restore a saved position.
  const members: Record<string, ViewGraph["elements"]> = {};
  for (const p of pools) members[p.slug] = [];
  const free: ViewGraph["elements"] = [];
  for (const e of vg.elements) {
    if (poolSet.has(e.slug)) continue;
    const parent = assignParent[e.slug];
    if (parent && poolSet.has(parent)) members[parent].push(e);
    else free.push(e);
  }

  const maxCols = Math.max(1, ...pools.map((p) => members[p.slug].length));
  const poolWidth = POOL_HEADER + PAD * 2 + maxCols * CHILD_W + (maxCols - 1) * GAP_X;
  const poolHeight = PAD * 2 + CHILD_H + 20;

  const nodes: CanvasNode[] = [];
  let py = 0;
  for (const p of pools) {
    const sp = saved.get(p.slug);
    const pos = sp && !sp.parent && (sp.x || sp.y) ? { x: sp.x, y: sp.y } : { x: 0, y: py };
    const pw = sp?.w && sp.w > 0 ? sp.w : poolWidth;
    const ph = sp?.h && sp.h > 0 ? sp.h : poolHeight;
    nodes.push({
      id: p.slug,
      type: "pool",
      position: pos,
      width: pw,
      height: ph,
      data: { element: p, kind: poolKind(reg, p.kind) ?? "pool" },
      style: { zIndex: 0 },
    });
    members[p.slug].forEach((m, i) => {
      const sm = saved.get(m.slug);
      const rel =
        sm && sm.parent === p.slug && (sm.x || sm.y)
          ? { x: sm.x, y: sm.y }
          : { x: POOL_HEADER + PAD + i * (CHILD_W + GAP_X), y: (ph - CHILD_H) / 2 };
      // No `extent: parent` — members must be draggable out to change pools.
      nodes.push({
        id: m.slug,
        type: "archimate",
        parentId: p.slug,
        position: rel,
        data: archiData(reg, m, sm?.style),
      });
    });
    py += ph + POOL_GAP;
  }

  free.forEach((e, i) => {
    const sf = saved.get(e.slug);
    const pos = sf && !sf.parent && (sf.x || sf.y) ? { x: sf.x, y: sf.y } : { x: i * (CHILD_W + GAP_X), y: py + 20 };
    nodes.push({ id: e.slug, type: "archimate", position: pos, data: archiData(reg, e, sf?.style) });
  });

  return nodes;
}

// ELK layered auto-layout (SPEC §3, §8.2). Returns a slug -> {x,y} map.
import ELK, { type ElkNode } from "elkjs/lib/elk.bundled.js";

const elk = new ELK();

export const NODE_W = 180;
export const NODE_H = 68;

export interface LayoutInput {
  id: string;
  width?: number;
  height?: number;
}

export async function layoutNodes(
  nodes: LayoutInput[],
  edges: { source: string; target: string }[],
  direction: "RIGHT" | "DOWN" = "RIGHT",
): Promise<Record<string, { x: number; y: number }>> {
  const graph: ElkNode = {
    id: "root",
    layoutOptions: {
      "elk.algorithm": "layered",
      "elk.direction": direction,
      "elk.spacing.nodeNode": "60",
      "elk.layered.spacing.nodeNodeBetweenLayers": "90",
    },
    children: nodes.map((n) => ({ id: n.id, width: n.width ?? NODE_W, height: n.height ?? NODE_H })),
    edges: edges.map((e, i) => ({ id: `e${i}`, sources: [e.source], targets: [e.target] })),
  };
  const res = await elk.layout(graph);
  const pos: Record<string, { x: number; y: number }> = {};
  for (const child of res.children ?? []) {
    pos[child.id] = { x: child.x ?? 0, y: child.y ?? 0 };
  }
  return pos;
}

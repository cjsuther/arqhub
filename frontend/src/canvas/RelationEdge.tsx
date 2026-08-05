import {
  BaseEdge,
  EdgeLabelRenderer,
  useInternalNode,
  type Edge,
  type EdgeProps,
} from "@xyflow/react";

import { getEdgeParams } from "./floating";

export interface RelEdgeData extends Record<string, unknown> {
  kind: string;
  label?: string | null;
  parallelIndex?: number; // position among edges sharing the same node pair
  parallelCount?: number; // how many edges share the pair
  stroke?: string; // per-view colour override (context menu)
}

export type RelEdge = Edge<RelEdgeData, "relation">;

interface EdgeVisual {
  dash?: string;
  markerEnd?: string;
  markerStart?: string;
}

// Line style + arrowheads per canonical relation (docs/archimate-notation.md).
function relationVisual(kind: string): EdgeVisual {
  switch (kind) {
    case "serving":
      return { markerEnd: "url(#am-arrow-open)" };
    case "triggering":
    case "sequence-flow":
      return { markerEnd: "url(#am-arrow-filled)" };
    case "flow":
    case "message-flow":
      return { dash: "6 4", markerEnd: "url(#am-arrow-filled)" };
    case "access":
      return { dash: "2 3", markerEnd: "url(#am-arrow-open)" };
    case "influence":
      return { dash: "5 4", markerEnd: "url(#am-arrow-open)" };
    case "realization":
      return { dash: "2 3", markerEnd: "url(#am-tri-hollow)" };
    case "specialization":
      return { markerEnd: "url(#am-tri-hollow)" };
    case "composition":
      return { markerStart: "url(#am-diamond-filled)" };
    case "aggregation":
      return { markerStart: "url(#am-diamond-hollow)" };
    case "assignment":
      return { markerStart: "url(#am-ball)", markerEnd: "url(#am-arrow-filled)" };
    case "association":
      return {};
    default:
      return { markerEnd: "url(#am-arrow-open)" };
  }
}

const PARALLEL_SPACING = 28; // px between stacked edges of the same node pair

export function RelationEdge(props: EdgeProps<RelEdge>) {
  const { id, source, target, data } = props;
  const sourceNode = useInternalNode(source);
  const targetNode = useInternalNode(target);

  // Floating endpoints (attach to the facing side); fall back to the handle-based
  // coordinates React Flow provides until the nodes are measured, so an edge is
  // never dropped.
  let sx = props.sourceX;
  let sy = props.sourceY;
  let tx = props.targetX;
  let ty = props.targetY;
  if (sourceNode && targetNode) {
    const p = getEdgeParams(sourceNode, targetNode);
    sx = p.sx;
    sy = p.sy;
    tx = p.tx;
    ty = p.ty;
  }

  // Separate parallel edges: bow each one by a perpendicular offset so multiple
  // relations between the same two components don't overlap.
  const count = data?.parallelCount ?? 1;
  const index = data?.parallelIndex ?? 0;
  const spread = (index - (count - 1) / 2) * PARALLEL_SPACING;

  const mx = (sx + tx) / 2;
  const my = (sy + ty) / 2;
  const dx = tx - sx;
  const dy = ty - sy;
  const len = Math.hypot(dx, dy) || 1;
  const nx = -dy / len; // unit perpendicular
  const ny = dx / len;
  const cx = mx + nx * spread * 2;
  const cy = my + ny * spread * 2;

  const path = `M ${sx},${sy} Q ${cx},${cy} ${tx},${ty}`;
  const labelX = mx + nx * spread;
  const labelY = my + ny * spread;

  const kind = data?.kind ?? "association";
  const v = relationVisual(kind);
  const stroke = data?.stroke || "#64748b";
  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={v.markerEnd}
        markerStart={v.markerStart}
        style={{ stroke, strokeWidth: 1.5, strokeDasharray: v.dash }}
      />
      <EdgeLabelRenderer>
        <div
          className="nodrag nopan pointer-events-none absolute rounded bg-white/85 px-1 text-[10px] text-slate-600"
          style={{ transform: `translate(-50%,-50%) translate(${labelX}px,${labelY}px)` }}
        >
          {kind}
          {data?.label ? `: ${data.label}` : ""}
        </div>
      </EdgeLabelRenderer>
    </>
  );
}

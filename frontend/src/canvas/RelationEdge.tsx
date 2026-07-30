import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  type Edge,
  type EdgeProps,
} from "@xyflow/react";

export interface RelEdgeData extends Record<string, unknown> {
  kind: string;
  label?: string | null;
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

export function RelationEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
}: EdgeProps<RelEdge>) {
  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 8,
  });
  const kind = data?.kind ?? "association";
  const v = relationVisual(kind);
  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={v.markerEnd}
        markerStart={v.markerStart}
        style={{ stroke: "#64748b", strokeWidth: 1.5, strokeDasharray: v.dash }}
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

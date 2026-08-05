import { Handle, NodeResizer, Position, type Node, type NodeProps } from "@xyflow/react";
import { Fragment } from "react";

import type { Element } from "../lib/types";

export interface PoolNodeData extends Record<string, unknown> {
  element: Element;
  kind: "pool" | "lane";
}

export type PoolNode = Node<PoolNodeData, "pool">;

export const POOL_HEADER = 30; // width of the left title band

const SIDES: [Position, string][] = [
  [Position.Left, "l"],
  [Position.Right, "r"],
  [Position.Top, "t"],
  [Position.Bottom, "b"],
];

// A BPMN pool/lane: a horizontal swimlane container. Child flow nodes are nested
// inside via React Flow's parentId; this renders the frame + the vertical label.
export function PoolNodeView({ data, selected }: NodeProps<PoolNode>) {
  const { element, kind } = data;
  const border = selected ? "#1e293b" : "#94a3b8";
  const band = kind === "lane" ? "rgba(0,0,0,.04)" : "rgba(99,102,241,.10)";
  return (
    <div
      className="relative h-full w-full rounded-md border-2"
      style={{ borderColor: border, background: "rgba(255,255,255,.35)" }}
    >
      <NodeResizer isVisible={!!selected} minWidth={240} minHeight={80} lineClassName="!border-slate-400" handleClassName="!h-2 !w-2 !bg-slate-500" />
      {SIDES.map(([pos, id]) => (
        <Fragment key={id}>
          <Handle id={`${id}-t`} type="target" position={pos} className="!h-2.5 !w-2.5 !border-0 !bg-transparent" />
          <Handle id={`${id}-s`} type="source" position={pos} className="!h-2 !w-2 !bg-slate-400" />
        </Fragment>
      ))}
      <div
        className="absolute inset-y-0 left-0 flex items-center justify-center border-r"
        style={{ width: POOL_HEADER, background: band, borderColor: border }}
      >
        <span
          className="max-h-full truncate text-[11px] font-semibold uppercase tracking-wide text-slate-600"
          style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}
          title={element.name}
        >
          {element.name}
        </span>
      </div>
    </div>
  );
}

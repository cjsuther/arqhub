import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";

import type { Element } from "../lib/types";
import { kindIcon, layerStyle } from "./style";

export interface ArchiNodeData extends Record<string, unknown> {
  element: Element;
  layer: string;
}

export type ArchiNode = Node<ArchiNodeData, "archimate">;

// Handles on all four sides; with ConnectionMode.Loose any can start/end an edge.
const SIDES: [Position, string][] = [
  [Position.Left, "l"],
  [Position.Right, "r"],
  [Position.Top, "t"],
  [Position.Bottom, "b"],
];

export function ArchiMateNode({ data, selected }: NodeProps<ArchiNode>) {
  const { element, layer } = data;
  const s = layerStyle(layer);
  const Icon = kindIcon(element.kind);
  const deprecated = element.lifecycle === "deprecated" || element.lifecycle === "retired";

  return (
    <div
      style={{
        background: s.bg,
        borderColor: selected ? "#1e293b" : s.border,
        color: s.text,
        opacity: deprecated ? 0.6 : 1,
      }}
      className="relative w-[180px] rounded-md border-2 px-3 py-2 shadow-sm"
      title={element.description ?? element.name}
    >
      {SIDES.map(([pos, id]) => (
        <Handle key={id} id={id} type="source" position={pos} className="!h-2 !w-2 !bg-slate-400" />
      ))}
      <div className="flex items-center justify-between gap-1">
        <span className="truncate text-[10px] font-semibold uppercase tracking-wide opacity-70">
          {element.kind}
        </span>
        <Icon size={13} className="shrink-0 opacity-70" />
      </div>
      <div className="mt-0.5 line-clamp-2 text-[13px] font-semibold leading-tight">
        {element.name}
      </div>
    </div>
  );
}

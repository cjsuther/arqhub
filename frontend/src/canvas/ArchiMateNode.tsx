import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";

import type { Element, Lang } from "../lib/types";
import { kindIcon, layerStyle } from "./style";

export interface ArchiNodeData extends Record<string, unknown> {
  element: Element;
  layer: string;
  lang: Lang;
}

export type ArchiNode = Node<ArchiNodeData, "archimate">;

const SIDES: [Position, string][] = [
  [Position.Left, "l"],
  [Position.Right, "r"],
  [Position.Top, "t"],
  [Position.Bottom, "b"],
];

function Handles() {
  return (
    <>
      {SIDES.map(([pos, id]) => (
        <Handle key={id} id={id} type="source" position={pos} className="!h-2 !w-2 !bg-slate-400" />
      ))}
    </>
  );
}

// BPMN is colour-neutral; use one soft palette and distinguish by shape.
const BPMN = { bg: "#eef2ff", border: "#6366f1", text: "#312e81" };

export function ArchiMateNode({ data, selected }: NodeProps<ArchiNode>) {
  const { element, layer, lang } = data;
  const Icon = kindIcon(element.kind);
  const deprecated = element.lifecycle === "deprecated" || element.lifecycle === "retired";
  const sel = selected ? "#1e293b" : "";
  const wrap = "relative flex flex-col items-center";

  // --- BPMN: shape carries the meaning ---
  if (lang === "bpmn") {
    if (element.kind === "event") {
      return (
        <div className={wrap} style={{ opacity: deprecated ? 0.6 : 1 }}>
          <Handles />
          <div
            className="flex h-[54px] w-[54px] items-center justify-center rounded-full border-2"
            style={{ background: BPMN.bg, borderColor: sel || BPMN.border, color: BPMN.text }}
          >
            <Icon size={18} />
          </div>
          <span className="mt-1 max-w-[120px] truncate text-[11px] font-medium">{element.name}</span>
        </div>
      );
    }
    if (element.kind === "gateway") {
      return (
        <div className={wrap} style={{ opacity: deprecated ? 0.6 : 1 }}>
          <Handles />
          <div
            className="flex h-[46px] w-[46px] rotate-45 items-center justify-center border-2"
            style={{ background: BPMN.bg, borderColor: sel || BPMN.border, color: BPMN.text }}
          >
            <Icon size={16} className="-rotate-45" />
          </div>
          <span className="mt-1 max-w-[120px] truncate text-[11px] font-medium">{element.name}</span>
        </div>
      );
    }
    return (
      <div
        className="relative w-[170px] rounded-xl border-2 px-3 py-2.5 shadow-sm"
        style={{ background: BPMN.bg, borderColor: sel || BPMN.border, color: BPMN.text, opacity: deprecated ? 0.6 : 1 }}
      >
        <Handles />
        <div className="flex items-center gap-1.5">
          <Icon size={13} className="shrink-0 opacity-70" />
          <span className="line-clamp-2 text-[13px] font-semibold leading-tight">{element.name}</span>
        </div>
      </div>
    );
  }

  // --- UML: stereotype header ---
  if (lang === "uml") {
    return (
      <div
        className="relative w-[180px] rounded-sm border-2 bg-white px-3 py-2 shadow-sm dark:bg-slate-100"
        style={{ borderColor: sel || "#475569", color: "#1e293b", opacity: deprecated ? 0.6 : 1 }}
      >
        <Handles />
        <div className="text-center text-[10px] italic text-slate-500">
          «{kindProjectionLabel(element.kind)}»
        </div>
        <div className="line-clamp-2 text-center text-[13px] font-semibold leading-tight">
          {element.name}
        </div>
      </div>
    );
  }

  // --- ArchiMate: colour by layer, type icon top-right ---
  const s = layerStyle(layer);
  return (
    <div
      className="relative w-[180px] rounded-md border-2 px-3 py-2 shadow-sm"
      style={{ background: s.bg, borderColor: sel || s.border, color: s.text, opacity: deprecated ? 0.6 : 1 }}
      title={element.description ?? element.name}
    >
      <Handles />
      <div className="flex items-center justify-between gap-1">
        <span className="truncate text-[10px] font-semibold uppercase tracking-wide opacity-70">
          {element.kind}
        </span>
        <Icon size={13} className="shrink-0 opacity-70" />
      </div>
      <div className="mt-0.5 line-clamp-2 text-[13px] font-semibold leading-tight">{element.name}</div>
    </div>
  );
}

function kindProjectionLabel(kind: string): string {
  const map: Record<string, string> = {
    "app-component": "component",
    actor: "actor",
    role: "actor",
    "data-object": "class",
    interface: "interface",
    service: "interface",
    process: "activity",
    task: "action",
  };
  return map[kind] ?? kind;
}

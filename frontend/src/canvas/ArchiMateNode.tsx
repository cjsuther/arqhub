import { Handle, Position, type Node, type NodeProps } from "@xyflow/react";
import { Link2 } from "lucide-react";
import { Fragment, type CSSProperties, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import type { Element, Lang } from "../lib/types";
import { linkedView } from "./drilldown";
import { kindIcon, layerStyle } from "./style";

// Per-view presentation overrides set from the context menu (stored in the
// view's layout, never in the model). Empty keys fall back to the layer/lang defaults.
export interface NodeStyleOverride {
  borderColor?: string;
  background?: string;
}

export interface ArchiNodeData extends Record<string, unknown> {
  element: Element;
  layer: string;
  lang: Lang;
  projection: string | null; // concrete type in the view's language (registry)
  style?: NodeStyleOverride;
}

// A small badge marking an element that drills down into another view; click it
// (or double-click the node) to open the linked view.
function NavBadge({ element }: { element: Element }) {
  const navigate = useNavigate();
  const target = linkedView(element);
  if (!target) return null;
  return (
    <button
      title={`Abrir la vista «${target}»`}
      onClick={(e) => { e.stopPropagation(); navigate(`/views/${target}/edit`); }}
      className="nodrag absolute -right-2 -top-2 z-10 flex h-4 w-4 items-center justify-center rounded-full bg-[hsl(var(--accent))] text-white shadow transition hover:scale-110"
    >
      <Link2 size={10} />
    </button>
  );
}

export type ArchiNode = Node<ArchiNodeData, "archimate">;

const SIDES: [Position, string][] = [
  [Position.Left, "l"],
  [Position.Right, "r"],
  [Position.Top, "t"],
  [Position.Bottom, "b"],
];

function Handles() {
  // Each side carries both a source and a target handle so an edge can resolve
  // an endpoint on any side (rendering) and a connection can start/end anywhere
  // (ConnectionMode.Loose). The target handle sits under the source, invisible.
  return (
    <>
      {SIDES.map(([pos, id]) => (
        <Fragment key={id}>
          <Handle id={`${id}-t`} type="target" position={pos} className="!h-2.5 !w-2.5 !border-0 !bg-transparent" />
          <Handle id={`${id}-s`} type="source" position={pos} className="!h-2 !w-2 !bg-slate-400" />
        </Fragment>
      ))}
    </>
  );
}

const BPMN = { bg: "#eef2ff", border: "#6366f1", text: "#312e81" };
const UML = { bg: "#ffffff", border: "#475569", text: "#1e293b" };

export function ArchiMateNode(props: NodeProps<ArchiNode>) {
  const { lang } = props.data;
  if (lang === "bpmn") return <BpmnShape {...props} />;
  if (lang === "uml") return <UmlShape {...props} />;
  return <ArchimateShape {...props} />;
}

// --- ArchiMate: rectangle coloured by layer, type icon top-right --------------
function ArchimateShape({ data, selected }: NodeProps<ArchiNode>) {
  const { element, layer } = data;
  const s = layerStyle(layer);
  const ov = data.style ?? {};
  const Icon = kindIcon(element.kind);
  const dep = element.lifecycle === "deprecated" || element.lifecycle === "retired";
  return (
    <div
      className="relative w-[180px] rounded-md border-2 px-3 py-2 shadow-sm"
      style={{ background: ov.background ?? s.bg, borderColor: selected ? "#1e293b" : ov.borderColor ?? s.border, color: s.text, opacity: dep ? 0.6 : 1 }}
      title={element.description ?? element.name}
    >
      <NavBadge element={element} />
      <Handles />
      <div className="flex items-center justify-between gap-1">
        <span className="truncate text-[10px] font-semibold uppercase tracking-wide opacity-70">{element.kind}</span>
        <Icon size={13} className="shrink-0 opacity-70" />
      </div>
      <div className="mt-0.5 line-clamp-2 text-[13px] font-semibold leading-tight">{element.name}</div>
    </div>
  );
}

// --- BPMN: shape carries the meaning -----------------------------------------
function BpmnShape({ data, selected }: NodeProps<ArchiNode>) {
  const { element, projection } = data;
  const ov = data.style ?? {};
  const Icon = kindIcon(element.kind);
  const border = selected ? "#1e293b" : ov.borderColor ?? BPMN.border;
  const dep = element.lifecycle === "deprecated" || element.lifecycle === "retired";
  const wrap = "relative flex flex-col items-center";
  const style = { background: ov.background ?? BPMN.bg, borderColor: border, color: BPMN.text, opacity: dep ? 0.6 : 1 };

  if (projection === null) return <NoProjection element={element} selected={selected} label="BPMN" />;

  if (element.kind === "event" || projection === "Event") {
    return (
      <div className={wrap} style={{ opacity: dep ? 0.6 : 1 }}>
        <Handles />
        <NavBadge element={element} />
        <div className="flex h-[54px] w-[54px] items-center justify-center rounded-full border-2" style={style}>
          <Icon size={18} />
        </div>
        <Label>{element.name}</Label>
      </div>
    );
  }
  if (element.kind === "gateway" || projection === "Gateway") {
    return (
      <div className={wrap} style={{ opacity: dep ? 0.6 : 1 }}>
        <Handles />
        <NavBadge element={element} />
        <div className="flex h-[46px] w-[46px] rotate-45 items-center justify-center border-2" style={style}>
          <Icon size={16} className="-rotate-45" />
        </div>
        <Label>{element.name}</Label>
      </div>
    );
  }
  if (projection === "DataObject") {
    return (
      <div className={wrap} style={{ opacity: dep ? 0.6 : 1 }}>
        <Handles />
        <NavBadge element={element} />
        <DocumentShape style={style} />
        <Label>{element.name}</Label>
      </div>
    );
  }
  if (projection === "Participant" || projection === "Lane") {
    // Pool / Lane: container rect with a left header band.
    return (
      <div className="relative flex h-16 w-[200px] overflow-hidden rounded border-2 shadow-sm" style={style}>
        <Handles />
        <div className="flex w-6 items-center justify-center border-r" style={{ borderColor: border, background: "rgba(0,0,0,.06)" }}>
          <span className="text-[9px] font-semibold uppercase">{projection === "Lane" ? "lane" : "pool"}</span>
        </div>
        <div className="flex flex-1 items-center px-2">
          <span className="line-clamp-2 text-[13px] font-semibold leading-tight">{element.name}</span>
        </div>
      </div>
    );
  }
  // Task / Process — rounded activity.
  return (
    <div className="relative w-[170px] rounded-xl border-2 px-3 py-2.5 shadow-sm" style={style}>
      <Handles />
      <NavBadge element={element} />
      <div className="flex items-center gap-1.5">
        <Icon size={13} className="shrink-0 opacity-70" />
        <span className="line-clamp-2 text-[13px] font-semibold leading-tight">{element.name}</span>
      </div>
    </div>
  );
}

// --- UML: component tabs, actor stickman, class compartments ------------------
function UmlShape({ data, selected }: NodeProps<ArchiNode>) {
  const { element, projection } = data;
  const ov = data.style ?? {};
  const border = selected ? "#1e293b" : ov.borderColor ?? UML.border;
  const dep = element.lifecycle === "deprecated" || element.lifecycle === "retired";
  const style = { background: ov.background ?? UML.bg, borderColor: border, color: UML.text, opacity: dep ? 0.6 : 1 };

  if (projection === null) return <NoProjection element={element} selected={selected} label="UML" />;

  if (projection === "Actor") {
    return (
      <div className="relative flex flex-col items-center" style={{ opacity: dep ? 0.6 : 1 }}>
        <Handles />
        <NavBadge element={element} />
        <svg width="34" height="46" viewBox="0 0 34 46" stroke={border} strokeWidth="2" fill="none">
          <circle cx="17" cy="8" r="6" />
          <line x1="17" y1="14" x2="17" y2="30" />
          <line x1="6" y1="20" x2="28" y2="20" />
          <line x1="17" y1="30" x2="7" y2="44" />
          <line x1="17" y1="30" x2="27" y2="44" />
        </svg>
        <Label>{element.name}</Label>
      </div>
    );
  }
  if (projection === "DecisionNode") {
    return (
      <div className="relative flex flex-col items-center" style={{ opacity: dep ? 0.6 : 1 }}>
        <Handles />
        <NavBadge element={element} />
        <div className="h-[42px] w-[42px] rotate-45 border-2" style={style} />
        <Label>{element.name}</Label>
      </div>
    );
  }
  if (projection === "Component") {
    return (
      <div className="relative w-[180px] rounded-sm border-2 py-2 pl-5 pr-3 shadow-sm" style={style}>
        <Handles />
        <NavBadge element={element} />
        {/* component tabs on the left edge */}
        <span className="absolute -left-[6px] top-3 h-2.5 w-3 border-2" style={{ background: UML.bg, borderColor: border }} />
        <span className="absolute -left-[6px] top-7 h-2.5 w-3 border-2" style={{ background: UML.bg, borderColor: border }} />
        <div className="text-center text-[10px] italic text-slate-500">«component»</div>
        <div className="line-clamp-2 text-center text-[13px] font-semibold leading-tight">{element.name}</div>
      </div>
    );
  }
  if (projection === "Class") {
    return (
      <div className="relative w-[180px] rounded-sm border-2 shadow-sm" style={style}>
        <Handles />
        <NavBadge element={element} />
        <div className="border-b px-2 py-1.5 text-center text-[13px] font-semibold leading-tight" style={{ borderColor: border }}>
          {element.name}
        </div>
        <div className="h-3 border-b" style={{ borderColor: border }} />
        <div className="h-3" />
      </div>
    );
  }
  // Interface / Signal / Activity / generic — stereotype header.
  return (
    <div className="relative w-[180px] rounded-sm border-2 px-3 py-2 shadow-sm" style={style}>
      <Handles />
      <NavBadge element={element} />
      <div className="text-center text-[10px] italic text-slate-500">«{(projection ?? element.kind).toLowerCase()}»</div>
      <div className="line-clamp-2 text-center text-[13px] font-semibold leading-tight">{element.name}</div>
    </div>
  );
}

// --- shared bits -------------------------------------------------------------
function Label({ children }: { children: ReactNode }) {
  return <span className="mt-1 max-w-[130px] truncate text-[11px] font-medium">{children}</span>;
}

function DocumentShape({ style }: { style: CSSProperties }) {
  return (
    <div className="relative h-[54px] w-[46px] border-2" style={{ ...style, clipPath: "polygon(0 0, 70% 0, 100% 22%, 100% 100%, 0 100%)" }}>
      <span className="absolute right-0 top-0 h-3 w-3 border-l-2 border-b-2" style={{ borderColor: style.borderColor }} />
    </div>
  );
}

function NoProjection({ element, selected, label }: { element: Element; selected: boolean; label: string }) {
  return (
    <div
      className="relative w-[170px] rounded-md border-2 border-dashed px-3 py-2"
      style={{ borderColor: selected ? "#1e293b" : "#94a3b8", color: "#64748b" }}
      title={`'${element.kind}' no tiene representación en ${label}`}
    >
      <Handles />
      <div className="text-[10px] uppercase tracking-wide">{element.kind}</div>
      <div className="line-clamp-2 text-[13px] font-medium leading-tight">{element.name}</div>
      <div className="mt-0.5 text-[9px] italic">sin representación {label}</div>
    </div>
  );
}

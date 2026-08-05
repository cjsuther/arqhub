// Right-click menu for canvas nodes and edges: colour overrides (presentation,
// stored in the view layout), lifecycle (model), drill-down link to a view, and
// removal. Edges get colour + delete.
import { ArrowRightCircle, Link2, Palette, Pencil, Trash2, Unlink } from "lucide-react";
import type { ReactNode } from "react";

import type { Element, Lifecycle, View } from "../lib/types";
import type { NodeStyleOverride } from "./ArchiMateNode";
import { linkedView } from "./drilldown";

const BORDER_SWATCHES = ["#e0b93f", "#4f9dde", "#5cb85c", "#9b7ede", "#ef4444", "#f97316", "#0ea5e9", "#64748b"];
const FILL_SWATCHES = ["#fdf3d0", "#dcecfb", "#d9f0d9", "#e7ddf7", "#fee2e2", "#ffedd5", "#e0f2fe", "#ffffff"];
const EDGE_SWATCHES = ["#64748b", "#ef4444", "#4f9dde", "#5cb85c", "#f97316", "#9b7ede", "#1e293b"];

const LIFECYCLES: { value: Lifecycle; label: string }[] = [
  { value: "proposed", label: "Propuesto" },
  { value: "active", label: "Activo" },
  { value: "deprecated", label: "Obsoleto" },
  { value: "retired", label: "Retirado" },
];

export type MenuTarget =
  | { type: "node"; element: Element; style?: NodeStyleOverride }
  | { type: "edge"; slug: string; kind: string; label?: string | null; stroke?: string };

interface Props {
  x: number;
  y: number;
  target: MenuTarget;
  views: View[];
  currentViewSlug: string;
  onClose: () => void;
  onNodeStyle: (patch: NodeStyleOverride) => void;
  onLifecycle: (lc: Lifecycle) => void;
  onLink: (viewSlug: string | null) => void;
  onNavigate: () => void;
  onRemoveFromView: () => void;
  onEdgeStroke: (color: string | null) => void;
  onRenameEdge: (label: string | null) => void;
  onDeleteEdge: () => void;
}

function Swatches({ colors, onPick }: { colors: string[]; onPick: (c: string) => void }) {
  return (
    <div className="flex flex-wrap gap-1 px-2 py-1">
      {colors.map((c) => (
        <button key={c} className="h-5 w-5 rounded border border-black/20 hover:scale-110"
          style={{ background: c }} onClick={() => onPick(c)} title={c} />
      ))}
    </div>
  );
}

function Section({ label, icon }: { label: string; icon: ReactNode }) {
  return (
    <div className="flex items-center gap-1.5 px-2 pt-1.5 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--muted))]">
      {icon} {label}
    </div>
  );
}

export function CanvasContextMenu(props: Props) {
  const { x, y, target, views, currentViewSlug, onClose } = props;
  const wrap = (fn: () => void) => () => { fn(); onClose(); };

  return (
    <>
      {/* Backdrop: click / right-click anywhere closes the menu. */}
      <div className="fixed inset-0 z-40" onClick={onClose}
        onContextMenu={(e) => { e.preventDefault(); onClose(); }} />
      <div
        className="surface fixed z-50 min-w-52 rounded-lg border py-1 text-sm shadow-lg"
        style={{ left: x, top: y }}
        onClick={(e) => e.stopPropagation()}
      >
        {target.type === "node" ? (
          <>
            <Section label="Color de borde" icon={<Palette size={12} />} />
            <Swatches colors={BORDER_SWATCHES} onPick={(c) => { props.onNodeStyle({ borderColor: c }); onClose(); }} />
            <Section label="Color de relleno" icon={<Palette size={12} />} />
            <Swatches colors={FILL_SWATCHES} onPick={(c) => { props.onNodeStyle({ background: c }); onClose(); }} />
            <button className="menu-item w-full px-3 py-1 text-left text-xs text-[hsl(var(--muted))] hover:bg-black/5 dark:hover:bg-white/5"
              onClick={wrap(() => props.onNodeStyle({ borderColor: undefined, background: undefined }))}>
              Restablecer colores
            </button>

            <div className="my-1 border-t" />
            <Section label="Estado" icon={<span className="h-2 w-2 rounded-full bg-current" />} />
            <div className="flex flex-wrap gap-1 px-2 py-1">
              {LIFECYCLES.map((lc) => (
                <button key={lc.value}
                  className={`rounded px-2 py-0.5 text-xs hover:bg-black/5 dark:hover:bg-white/5 ${
                    target.element.lifecycle === lc.value ? "bg-[hsl(var(--accent))]/15 font-medium" : "border"
                  }`}
                  onClick={wrap(() => props.onLifecycle(lc.value))}>
                  {lc.label}
                </button>
              ))}
            </div>

            <div className="my-1 border-t" />
            <div className="px-2 py-1">
              <div className="mb-1 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-[hsl(var(--muted))]">
                <Link2 size={12} /> Navegar a vista
              </div>
              <select
                className="input w-full !py-1 text-xs"
                value={linkedView(target.element) ?? ""}
                onChange={(e) => { props.onLink(e.target.value || null); onClose(); }}
              >
                <option value="">— ninguna —</option>
                {views.filter((v) => v.slug !== currentViewSlug).map((v) => (
                  <option key={v.slug} value={v.slug}>{v.name}</option>
                ))}
              </select>
              {linkedView(target.element) && (
                <button className="mt-1 flex w-full items-center gap-1.5 rounded px-1 py-1 text-left text-xs text-[hsl(var(--accent))] hover:bg-black/5 dark:hover:bg-white/5"
                  onClick={wrap(props.onNavigate)}>
                  <ArrowRightCircle size={13} /> Ir a la vista vinculada
                </button>
              )}
            </div>

            <div className="my-1 border-t" />
            <button className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-red-600 hover:bg-red-500/10"
              onClick={wrap(props.onRemoveFromView)}>
              <Unlink size={14} /> Quitar de la vista
            </button>
          </>
        ) : (
          <>
            <div className="px-3 py-1 text-xs text-[hsl(var(--muted))]">
              Relación: <code>{target.kind}</code>{target.label ? ` · ${target.label}` : ""}
            </div>
            <button className="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-black/5 dark:hover:bg-white/5"
              onClick={() => {
                const next = window.prompt("Nombre del conector:", target.label ?? "");
                if (next !== null) { props.onRenameEdge(next.trim() || null); onClose(); }
              }}>
              <Pencil size={14} /> Renombrar
            </button>
            <div className="my-1 border-t" />
            <Section label="Color" icon={<Palette size={12} />} />
            <Swatches colors={EDGE_SWATCHES} onPick={(c) => { props.onEdgeStroke(c); onClose(); }} />
            <button className="w-full px-3 py-1 text-left text-xs text-[hsl(var(--muted))] hover:bg-black/5 dark:hover:bg-white/5"
              onClick={wrap(() => props.onEdgeStroke(null))}>
              Restablecer color
            </button>
            <div className="my-1 border-t" />
            <button className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-red-600 hover:bg-red-500/10"
              onClick={wrap(props.onDeleteEdge)}>
              <Trash2 size={14} /> Eliminar relación
            </button>
          </>
        )}
      </div>
    </>
  );
}

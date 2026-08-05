import { useQuery } from "@tanstack/react-query";
import { Plus, Search } from "lucide-react";
import { useState } from "react";

import { api } from "../lib/api";
import type { Registry, View } from "../lib/types";
import { KindBadge } from "../lib/ui";

// DataTransfer key for dragging a catalog element onto the canvas.
export const CATALOG_DND = "application/arqhub-catalog";

interface Props {
  view: View;
  registry?: Registry;
  inView: Set<string>;
  onChanged: () => void;
}

export function Palette({ view, registry, inView, onChanged }: Props) {
  const [tab, setTab] = useState<"catalog" | "new">("catalog");
  return (
    <div className="surface flex w-64 flex-col border-r">
      <div className="flex border-b text-sm">
        {(["catalog", "new"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 py-2 font-medium ${tab === t ? "border-b-2 border-[hsl(var(--accent))]" : "text-[hsl(var(--muted))]"}`}
          >
            {t === "catalog" ? "Catálogo" : "Nuevo"}
          </button>
        ))}
      </div>
      {tab === "catalog" ? (
        <CatalogTab view={view} registry={registry} inView={inView} onChanged={onChanged} />
      ) : (
        <NewTab view={view} registry={registry} onChanged={onChanged} />
      )}
    </div>
  );
}

function CatalogTab({ view, registry, inView, onChanged }: Props) {
  const [q, setQ] = useState("");
  const elements = useQuery({ queryKey: ["elements", {}], queryFn: () => api.listElements() });
  const candidates = (elements.data ?? []).filter(
    (e) => !inView.has(e.slug) && `${e.name} ${e.slug}`.toLowerCase().includes(q.toLowerCase()),
  );

  async function add(slug: string) {
    await api.addElementsToView(view.slug, view, [slug]);
    onChanged();
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-2 p-2">
      <div className="relative">
        <Search size={14} className="absolute left-2 top-1/2 -translate-y-1/2 text-[hsl(var(--muted))]" />
        <input className="input w-full pl-7 text-sm" placeholder="Buscar elemento…"
          value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      <p className="text-xs text-[hsl(var(--muted))]">Arrastrá al lienzo para ubicarlo, o hacé clic para auto-posicionarlo.</p>
      <div className="min-h-0 flex-1 space-y-1 overflow-auto">
        {candidates.map((e) => (
          <button key={e.slug} onClick={() => add(e.slug)}
            draggable
            onDragStart={(ev) => ev.dataTransfer.setData(CATALOG_DND, e.slug)}
            className="flex w-full cursor-grab items-center justify-between gap-1 rounded border border-transparent px-2 py-1.5 text-left text-sm hover:surface hover:border-[hsl(var(--border))] active:cursor-grabbing">
            <span className="truncate">{e.name}</span>
            <KindBadge registry={registry} kind={e.kind} />
          </button>
        ))}
        {candidates.length === 0 && (
          <p className="px-2 py-4 text-center text-xs text-[hsl(var(--muted))]">Sin elementos para agregar.</p>
        )}
      </div>
    </div>
  );
}

function NewTab({ view, registry, onChanged }: { view: View; registry?: Registry; onChanged: () => void }) {
  const [name, setName] = useState("");
  const [kind, setKind] = useState("app-component");
  const [error, setError] = useState<string | null>(null);

  function slugify(text: string) {
    return text.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  }

  async function create() {
    setError(null);
    const slug = slugify(name);
    if (!slug) return setError("Poné un nombre.");
    try {
      await api.createElement({ slug, name, kind });
      await api.addElementsToView(view.slug, view, [slug]);
      setName("");
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message.slice(0, 120) : "Error");
    }
  }

  // Only kinds that project into the view's language.
  const kinds = registry
    ? Object.entries(registry.kinds).filter(([, k]) => k.mappings[view.lang]).map(([k]) => k)
    : [];

  return (
    <div className="flex flex-col gap-2 p-2 text-sm">
      <label className="text-xs font-medium text-[hsl(var(--muted))]">Nombre</label>
      <input className="input" value={name} onChange={(e) => setName(e.target.value)}
        placeholder="Ej: Motor de Scoring" />
      <label className="text-xs font-medium text-[hsl(var(--muted))]">Tipo</label>
      <select className="input" value={kind} onChange={(e) => setKind(e.target.value)}>
        {kinds.map((k) => <option key={k} value={k}>{k}</option>)}
      </select>
      {error && <p className="text-xs text-red-500">{error}</p>}
      <button className="btn btn-primary justify-center" onClick={create}>
        <Plus size={15} /> Crear y agregar
      </button>
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LayoutGrid, List, SlidersHorizontal } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { folderOptions } from "../../components/FolderSelect";
import { FoldersAside } from "../../components/FoldersAside";
import { ALL, DND_ITEM, UNFILED, descendants } from "../../components/FolderTree";
import { api } from "../../lib/api";
import type { Element } from "../../lib/types";
import { KindBadge, LifecycleBadge } from "../../lib/ui";
import { AdvancedSearchDialog } from "./AdvancedSearchDialog";
import { fieldTokenMap, matchElement, parseQuery } from "./search";

export function CatalogPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [advanced, setAdvanced] = useState(false);
  const [folder, setFolderState] = useState<string | null>(
    () => localStorage.getItem("arqhub:folders:element:selected") || ALL,
  );
  const setFolder = (id: string | null) => {
    setFolderState(id);
    if (id) localStorage.setItem("arqhub:folders:element:selected", id);
    else localStorage.removeItem("arqhub:folders:element:selected");
  };
  const [grouped, setGrouped] = useState(false);
  const [sort, setSort] = useState("name");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const registry = useQuery({ queryKey: ["registry"], queryFn: api.registry });
  const folders = useQuery({ queryKey: ["folders", "element"], queryFn: () => api.listFolders("element") });
  const allFields = useQuery({ queryKey: ["fields", "all"], queryFn: () => api.listFields() });
  // Distinct custom fields across every type (dedup by key), used to parse `field:value` tokens.
  const fieldOpts = [...new Map((allFields.data ?? []).map((f) => [f.key, f])).values()];
  const tokens = useMemo(() => fieldTokenMap(fieldOpts), [allFields.data]);
  const parsed = useMemo(() => parseQuery(q, tokens), [q, tokens]);
  // All filtering (text, tipo/ciclo, custom fields, ranges) runs client-side over the full list.
  const elements = useQuery({ queryKey: ["elements", "all"], queryFn: () => api.listElements({}) });

  const clearSel = () => setSelected(new Set());
  const toggle = (slug: string) =>
    setSelected((p) => {
      const n = new Set(p);
      n.has(slug) ? n.delete(slug) : n.add(slug);
      return n;
    });

  const move = useMutation({
    mutationFn: ({ slugs, folderId }: { slugs: string[]; folderId: string | null }) =>
      Promise.all(slugs.map((s) => api.setElementFolder(s, folderId))),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["elements"] });
      clearSel();
    },
  });
  const bulkMove = (value: string) => {
    if (!value) return;
    move.mutate({ slugs: [...selected], folderId: value === "__none__" ? null : value });
  };

  const subtree = folder && folder !== UNFILED ? descendants(folders.data ?? [], folder) : null;
  const inFolder = (e: Element) =>
    folder === ALL ? true : folder === UNFILED ? e.folder_id == null : !!e.folder_id && subtree!.has(e.folder_id);
  const sortKey = (e: Element) =>
    sort === "kind" ? e.kind : sort === "lifecycle" ? e.lifecycle : e.name;

  const visible = (elements.data ?? [])
    .filter(inFolder)
    .filter((e) => matchElement(e, parsed, tokens))
    .sort((a, b) => sortKey(a).localeCompare(sortKey(b)) || a.name.localeCompare(b.name));

  function card(el: Element) {
    const sel = selected.has(el.slug);
    const dragSlugs = sel ? [...selected] : [el.slug]; // dragging a selected card moves the whole selection
    return (
      <div key={el.slug} className="relative">
        <input type="checkbox" checked={sel} onChange={() => toggle(el.slug)}
          title="Seleccionar" className="absolute left-3 top-4 z-10 h-4 w-4 cursor-pointer" />
        <Link to={`/catalog/${el.slug}`} draggable
          onDragStart={(e) => e.dataTransfer.setData(DND_ITEM, dragSlugs.join(","))}
          className={`surface block rounded-lg border p-4 pl-9 transition hover:shadow-sm hover:-translate-y-0.5 ${
            sel ? "ring-2 ring-[hsl(var(--accent))]" : ""
          }`}>
          <div className="flex items-start justify-between gap-2">
            <h3 className="font-medium leading-tight">{el.name}</h3>
            <LifecycleBadge value={el.lifecycle} />
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <KindBadge registry={registry.data} kind={el.kind} />
            {el.domain && <span className="text-xs text-[hsl(var(--muted))]">{el.domain}</span>}
          </div>
          {el.description && <p className="mt-2 line-clamp-2 text-sm text-[hsl(var(--muted))]">{el.description}</p>}
        </Link>
      </div>
    );
  }

  const groups = grouped
    ? [...new Set(visible.map((e) => e.kind))].sort().map((k) => ({ k, items: visible.filter((e) => e.kind === k) }))
    : null;

  return (
    <div className="flex h-full gap-4">
      <FoldersAside scope="element" selected={folder} onSelect={setFolder}
        onDropItem={(folderId, slugs) => move.mutate({ slugs, folderId })} />

      <div className="min-w-0 flex-1 space-y-4">
        <div>
          <h1 className="text-xl font-semibold">Catálogo</h1>
          <p className="text-sm text-[hsl(var(--muted))]">
            Seleccioná varios y movelos en lote, o arrastralos a una carpeta. El catálogo <em>es</em> el modelo.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <input className="input flex-1 min-w-48"
            placeholder="Buscar: texto, o campo:valor  ·  rangos con ..  (ej: fecha-vencimiento:2026-08-01..2026-08-31)"
            value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="btn btn-ghost" onClick={() => setAdvanced(true)} title="Búsqueda avanzada por campos">
            <SlidersHorizontal size={15} /> Búsqueda avanzada
          </button>
          {q && <button className="btn btn-ghost" onClick={() => setQ("")} title="Limpiar búsqueda">Limpiar</button>}
          <select className="input" value={sort} onChange={(e) => setSort(e.target.value)} title="Ordenar por">
            <option value="name">Ordenar: Nombre</option>
            <option value="kind">Ordenar: Tipo</option>
            <option value="lifecycle">Ordenar: Ciclo de vida</option>
          </select>
          <button className="btn btn-ghost" onClick={() => setGrouped((g) => !g)} title="Agrupar por tipo">
            {grouped ? <List size={15} /> : <LayoutGrid size={15} />} {grouped ? "Lista" : "Agrupar"}
          </button>
        </div>

        {parsed.clauses.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 text-xs text-[hsl(var(--muted))]">
            <span>Filtros activos:</span>
            {parsed.clauses.map((c, i) => (
              <span key={i} className="badge bg-[hsl(var(--accent))]/15 text-[hsl(var(--accent))]">
                {c.token}: {c.op === "range" ? `${c.from ?? ""}..${c.to ?? ""}` : c.value}
              </span>
            ))}
          </div>
        )}

        {selected.size > 0 && (
          <div className="flex flex-wrap items-center gap-2 rounded-lg border bg-[hsl(var(--accent))]/10 px-3 py-2 text-sm">
            <span className="font-medium">{selected.size} seleccionado{selected.size > 1 ? "s" : ""}</span>
            <select className="input !py-1" value="" onChange={(e) => bulkMove(e.target.value)}>
              <option value="">Mover a carpeta…</option>
              <option value="__none__">Sin carpeta</option>
              {folderOptions(folders.data ?? []).map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
            </select>
            <button className="btn btn-ghost !py-1 ml-auto" onClick={clearSel}>Limpiar selección</button>
          </div>
        )}

        {elements.isError && <p className="text-sm text-red-500">Error al cargar. ¿Está el backend en :8000?</p>}

        {groups
          ? groups.map((g) => (
              <div key={g.k}>
                <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[hsl(var(--muted))]">
                  {g.k} <span className="font-normal">({g.items.length})</span>
                </h2>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{g.items.map(card)}</div>
              </div>
            ))
          : <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">{visible.map(card)}</div>}

        {visible.length === 0 && !elements.isLoading && (
          <p className="text-sm text-[hsl(var(--muted))]">No hay elementos en esta selección.</p>
        )}
      </div>

      {advanced && (
        <AdvancedSearchDialog
          initialQuery={q}
          fields={fieldOpts}
          kinds={Object.keys(registry.data?.kinds ?? {})}
          lifecycles={registry.data?.lifecycles ?? []}
          onApply={setQ}
          onClose={() => setAdvanced(false)}
        />
      )}
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LayoutGrid, List } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { folderOptions } from "../../components/FolderSelect";
import { FoldersAside } from "../../components/FoldersAside";
import { ALL, DND_ITEM, UNFILED, descendants } from "../../components/FolderTree";
import { api } from "../../lib/api";
import type { Element } from "../../lib/types";
import { KindBadge, LifecycleBadge } from "../../lib/ui";

export function CatalogPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("");
  const [lifecycle, setLifecycle] = useState("");
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

  const [fieldKey, setFieldKey] = useState("");
  const [fieldValue, setFieldValue] = useState("");

  const registry = useQuery({ queryKey: ["registry"], queryFn: api.registry });
  const folders = useQuery({ queryKey: ["folders", "element"], queryFn: () => api.listFolders("element") });
  const kindFields = useQuery({ queryKey: ["fields", kind], queryFn: () => api.listFields(kind), enabled: !!kind });
  const elements = useQuery({
    queryKey: ["elements", { q, kind, lifecycle, fieldKey, fieldValue }],
    queryFn: () =>
      api.listElements({
        q: q || undefined, kind: kind || undefined, lifecycle: lifecycle || undefined,
        field_key: fieldKey || undefined, field_value: fieldValue || undefined,
      }),
  });

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
          <input className="input flex-1 min-w-48" placeholder="Buscar por nombre o descripción…"
            value={q} onChange={(e) => setQ(e.target.value)} />
          <select className="input" value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="">Todos los tipos</option>
            {registry.data && Object.keys(registry.data.kinds).map((k) => <option key={k} value={k}>{k}</option>)}
          </select>
          <select className="input" value={lifecycle} onChange={(e) => setLifecycle(e.target.value)}>
            <option value="">Todo el ciclo de vida</option>
            {registry.data?.lifecycles.map((l) => <option key={l} value={l}>{l}</option>)}
          </select>
          <select className="input" value={sort} onChange={(e) => setSort(e.target.value)} title="Ordenar por">
            <option value="name">Ordenar: Nombre</option>
            <option value="kind">Ordenar: Tipo</option>
            <option value="lifecycle">Ordenar: Ciclo de vida</option>
          </select>
          <button className="btn btn-ghost" onClick={() => setGrouped((g) => !g)} title="Agrupar por tipo">
            {grouped ? <List size={15} /> : <LayoutGrid size={15} />} {grouped ? "Lista" : "Agrupar"}
          </button>
        </div>

        {kind && (kindFields.data?.length ?? 0) > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-[hsl(var(--muted))]">Filtrar por campo:</span>
            <select className="input" value={fieldKey} onChange={(e) => setFieldKey(e.target.value)}>
              <option value="">—</option>
              {kindFields.data!.map((f) => <option key={f.id} value={f.key}>{f.label}</option>)}
            </select>
            {fieldKey && (
              <input className="input flex-1 min-w-40" placeholder="Valor…" value={fieldValue}
                onChange={(e) => setFieldValue(e.target.value)} />
            )}
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
    </div>
  );
}

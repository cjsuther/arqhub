import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LayoutGrid, List } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { ALL, DND_ITEM, FolderTree, UNFILED, descendants } from "../../components/FolderTree";
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

  const registry = useQuery({ queryKey: ["registry"], queryFn: api.registry });
  const folders = useQuery({ queryKey: ["folders", "element"], queryFn: () => api.listFolders("element") });
  const elements = useQuery({
    queryKey: ["elements", { q, kind, lifecycle }],
    queryFn: () =>
      api.listElements({ q: q || undefined, kind: kind || undefined, lifecycle: lifecycle || undefined }),
  });

  const move = useMutation({
    mutationFn: ({ slug, folderId }: { slug: string; folderId: string | null }) =>
      api.setElementFolder(slug, folderId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["elements"] }),
  });

  const subtree = folder && folder !== UNFILED ? descendants(folders.data ?? [], folder) : null;
  const inFolder = (e: Element) =>
    folder === ALL ? true : folder === UNFILED ? e.folder_id == null : !!e.folder_id && subtree!.has(e.folder_id);
  const visible = (elements.data ?? []).filter(inFolder);

  function card(el: Element) {
    return (
      <Link key={el.slug} to={`/catalog/${el.slug}`} draggable
        onDragStart={(e) => e.dataTransfer.setData(DND_ITEM, el.slug)}
        className="surface block rounded-lg border p-4 transition hover:shadow-sm hover:-translate-y-0.5">
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
    );
  }

  const groups = grouped
    ? [...new Set(visible.map((e) => e.kind))].sort().map((k) => ({ k, items: visible.filter((e) => e.kind === k) }))
    : null;

  return (
    <div className="flex h-full gap-4">
      <aside className="surface w-56 shrink-0 overflow-auto rounded-lg border p-2">
        <FolderTree scope="element" selected={folder} onSelect={setFolder}
          onDropItem={(folderId, slug) => move.mutate({ slug, folderId })} />
      </aside>

      <div className="min-w-0 flex-1 space-y-4">
        <div>
          <h1 className="text-xl font-semibold">Catálogo</h1>
          <p className="text-sm text-[hsl(var(--muted))]">
            Arrastrá elementos a una carpeta para organizarlos. El catálogo <em>es</em> el modelo.
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
          <button className="btn btn-ghost" onClick={() => setGrouped((g) => !g)} title="Agrupar por tipo">
            {grouped ? <List size={15} /> : <LayoutGrid size={15} />} {grouped ? "Lista" : "Agrupar"}
          </button>
        </div>

        {elements.isError && <p className="text-sm text-red-500">Error al cargar. ¿Está el backend en :8000?</p>}

        {groups
          ? groups.map((g) => (
              <div key={g.k}>
                <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[hsl(var(--muted))]">
                  {g.k} <span className="font-normal">({g.items.length})</span>
                </h2>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">{g.items.map(card)}</div>
              </div>
            ))
          : <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">{visible.map(card)}</div>}

        {visible.length === 0 && !elements.isLoading && (
          <p className="text-sm text-[hsl(var(--muted))]">No hay elementos en esta selección.</p>
        )}
      </div>
    </div>
  );
}

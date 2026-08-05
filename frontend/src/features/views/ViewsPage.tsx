import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LayoutGrid, List, Plus, Search } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { ALL, DND_ITEM, FolderTree, UNFILED, descendants } from "../../components/FolderTree";
import { api } from "../../lib/api";
import type { View } from "../../lib/types";
import { StatusBadge, langLabel } from "../../lib/ui";
import { NewViewModal } from "./NewViewModal";

export function ViewsPage() {
  const qc = useQueryClient();
  const views = useQuery({ queryKey: ["views"], queryFn: api.listViews });
  const folders = useQuery({ queryKey: ["folders", "view"], queryFn: () => api.listFolders("view") });
  const [creating, setCreating] = useState(false);
  const [q, setQ] = useState("");
  const [folder, setFolderState] = useState<string | null>(
    () => localStorage.getItem("arqhub:folders:view:selected") || ALL,
  );
  const setFolder = (id: string | null) => {
    setFolderState(id);
    if (id) localStorage.setItem("arqhub:folders:view:selected", id);
    else localStorage.removeItem("arqhub:folders:view:selected");
  };
  const [grouped, setGrouped] = useState(false);

  const move = useMutation({
    mutationFn: ({ slug, folderId }: { slug: string; folderId: string | null }) =>
      api.setViewFolder(slug, folderId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["views"] }),
  });

  const subtree = folder && folder !== UNFILED ? descendants(folders.data ?? [], folder) : null;
  const visible = (views.data ?? []).filter((v) => {
    if (q && !v.name.toLowerCase().includes(q.toLowerCase())) return false;
    if (folder === ALL) return true;
    if (folder === UNFILED) return v.folder_id == null;
    return !!v.folder_id && subtree!.has(v.folder_id);
  });

  function card(v: View) {
    return (
      <Link key={v.slug} to={`/views/${v.slug}/edit`} draggable
        onDragStart={(e) => e.dataTransfer.setData(DND_ITEM, v.slug)}
        className="surface block rounded-lg border p-4 transition hover:shadow-sm hover:-translate-y-0.5">
        <div className="mb-3 flex aspect-video items-center justify-center overflow-hidden rounded-md bg-black/5 dark:bg-white/5">
          <img src={`/api/v1/views/${v.slug}/render`} alt={v.name} className="h-full w-full object-contain"
            onError={(e) => { e.currentTarget.style.display = "none"; }} />
          <LayoutGrid className="text-[hsl(var(--muted))]" />
        </div>
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-medium leading-tight">{v.name}</h3>
          <StatusBadge value={v.status} />
        </div>
        <div className="mt-2 flex items-center gap-2 text-xs text-[hsl(var(--muted))]">
          <span className="badge bg-black/5 dark:bg-white/10">{langLabel(v.lang)}</span>
          <span>v{v.current_version}</span>
          <span>· {v.include.elements.length} elementos</span>
        </div>
      </Link>
    );
  }

  const groups = grouped
    ? [...new Set(visible.map((v) => v.lang))].sort().map((l) => ({ l, items: visible.filter((v) => v.lang === l) }))
    : null;

  return (
    <div className="flex h-full gap-4">
      <aside className="surface w-56 shrink-0 overflow-auto rounded-lg border p-2">
        <FolderTree scope="view" selected={folder} onSelect={setFolder}
          onDropItem={(folderId, slug) => move.mutate({ slug, folderId })} />
      </aside>

      <div className="min-w-0 flex-1 space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-semibold">Vistas</h1>
            <p className="text-sm text-[hsl(var(--muted))]">Arrastrá vistas a carpetas para organizarlas.</p>
          </div>
          <button className="btn btn-primary" onClick={() => setCreating(true)}><Plus size={16} /> Nueva vista</button>
        </div>
        {creating && <NewViewModal onClose={() => setCreating(false)} />}

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative flex-1 min-w-48">
            <Search size={16} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--muted))]" />
            <input className="input w-full pl-8" placeholder="Buscar vista…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <button className="btn btn-ghost" onClick={() => setGrouped((g) => !g)} title="Agrupar por lenguaje">
            {grouped ? <List size={15} /> : <LayoutGrid size={15} />} {grouped ? "Lista" : "Agrupar"}
          </button>
        </div>

        {views.isError && <p className="text-sm text-red-500">Error al cargar. ¿Está el backend en :8000?</p>}

        {groups
          ? groups.map((g) => (
              <div key={g.l}>
                <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-[hsl(var(--muted))]">
                  {langLabel(g.l)} <span className="font-normal">({g.items.length})</span>
                </h2>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">{g.items.map(card)}</div>
              </div>
            ))
          : <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">{visible.map(card)}</div>}

        {visible.length === 0 && <p className="text-sm text-[hsl(var(--muted))]">No hay vistas en esta selección.</p>}
      </div>
    </div>
  );
}

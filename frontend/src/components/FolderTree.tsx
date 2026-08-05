import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ChevronDown, ChevronRight, Folder as FolderIcon, FolderPlus, Layers, Lock, Pencil, Shield, Trash2,
} from "lucide-react";
import { useState, type DragEvent, type ReactNode } from "react";

import { api } from "../lib/api";
import type { Folder } from "../lib/types";

export const ALL = null; // show everything
export const UNFILED = "__unfiled__"; // items with no folder
export const DND_ITEM = "application/arqhub-item";
export const DND_FOLDER = "application/arqhub-folder";

interface Props {
  scope: "element" | "view";
  selected: string | null;
  onSelect: (id: string | null) => void;
  onDropItem?: (folderId: string | null, itemIds: string[]) => void; // drag item(s) onto folder
}

interface TreeNode extends Folder {
  children: TreeNode[];
}

function buildTree(folders: Folder[]): TreeNode[] {
  const byId = new Map<string, TreeNode>(folders.map((f) => [f.id, { ...f, children: [] }]));
  const roots: TreeNode[] = [];
  for (const node of byId.values()) {
    if (node.parent_id && byId.has(node.parent_id)) byId.get(node.parent_id)!.children.push(node);
    else roots.push(node);
  }
  const sort = (ns: TreeNode[]) => {
    ns.sort((a, b) => a.name.localeCompare(b.name));
    ns.forEach((n) => sort(n.children));
  };
  sort(roots);
  return roots;
}

const EXPANDED_KEY = (scope: string) => `arqhub:folders:${scope}:expanded`;
function loadExpanded(scope: string): Set<string> {
  try {
    const raw = localStorage.getItem(EXPANDED_KEY(scope));
    return raw ? new Set<string>(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

export function FolderTree({ scope, selected, onSelect, onDropItem }: Props) {
  const qc = useQueryClient();
  const itemsKey = scope === "element" ? "elements" : "views";
  const folders = useQuery({ queryKey: ["folders", scope], queryFn: () => api.listFolders(scope) });
  const me = useQuery({ queryKey: ["me"], queryFn: api.getMe });
  const groupsQ = useQuery({ queryKey: ["groups"], queryFn: () => api.listGroups() });
  const [expanded, setExpanded] = useState<Set<string>>(() => loadExpanded(scope));
  const [permsFor, setPermsFor] = useState<string | null>(null);

  const isAdmin = me.data?.role === "admin";
  const groups = groupsQ.data ?? [];
  const restricted = new Set(groups.flatMap((g) => g.folder_ids)); // folders with any grant

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["folders", scope] });
    qc.invalidateQueries({ queryKey: [itemsKey] });
  };
  const createM = useMutation({ mutationFn: api.createFolder, onSuccess: invalidate });
  const updateM = useMutation({
    mutationFn: (v: { id: string; name: string }) => api.updateFolder(v.id, { name: v.name }),
    onSuccess: invalidate,
  });
  const deleteM = useMutation({ mutationFn: api.deleteFolder, onSuccess: invalidate });
  const reparentM = useMutation({
    mutationFn: (v: { id: string; parent_id: string | null }) => api.updateFolder(v.id, { parent_id: v.parent_id }),
    onSuccess: invalidate,
    onError: () => window.alert("No se puede mover ahí (crearía un ciclo)."),
  });
  const permM = useMutation({
    mutationFn: (v: { folderId: string; ids: string[] }) => api.setFolderGroups(v.folderId, v.ids),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["groups"] }),
  });

  const tree = buildTree(folders.data ?? []);

  function toggle(id: string) {
    setExpanded((p) => {
      const n = new Set(p);
      n.has(id) ? n.delete(id) : n.add(id);
      try { localStorage.setItem(EXPANDED_KEY(scope), JSON.stringify([...n])); } catch { /* ignore */ }
      return n;
    });
  }

  function addFolder(parentId: string | null) {
    const name = window.prompt("Nombre de la carpeta:")?.trim();
    if (name) createM.mutate({ name, scope, parent_id: parentId });
  }

  const dropHandlers = (id: string | null) => ({
    onDragOver: (e: DragEvent) => {
      if (e.dataTransfer.types.includes(DND_ITEM) || e.dataTransfer.types.includes(DND_FOLDER)) e.preventDefault();
    },
    onDrop: (e: DragEvent) => {
      const fdrag = e.dataTransfer.getData(DND_FOLDER);
      if (fdrag) {
        if (id === UNFILED) return; // folders reparent to a folder or to root ("Todas")
        const parent = id === ALL ? null : id;
        if (fdrag !== parent) reparentM.mutate({ id: fdrag, parent_id: parent });
        return;
      }
      if (onDropItem && id !== ALL) {
        const items = e.dataTransfer.getData(DND_ITEM).split(",").filter(Boolean);
        if (items.length) onDropItem(id === UNFILED ? null : id, items);
      }
    },
  });

  const row = (label: string, id: string | null, icon: ReactNode, depth = 0, extra?: ReactNode, dragId?: string) => (
    <div
      {...dropHandlers(id)}
      draggable={!!dragId}
      onDragStart={dragId ? (e) => e.dataTransfer.setData(DND_FOLDER, dragId) : undefined}
      className={`group flex items-center gap-1 rounded px-1.5 py-1 text-sm ${
        selected === id ? "bg-[hsl(var(--accent))]/15 font-medium" : "hover:bg-black/5 dark:hover:bg-white/5"
      }`}
      style={{ paddingLeft: 6 + depth * 14 }}
    >
      <button className="flex min-w-0 flex-1 items-center gap-1.5 text-left" onClick={() => onSelect(id)}>
        {icon}
        <span className="truncate">{label}</span>
      </button>
      {extra}
    </div>
  );

  const renderNode = (node: TreeNode, depth: number): ReactNode => {
    const hasChildren = node.children.length > 0;
    const isOpen = expanded.has(node.id);
    const nodeGroups = groups.filter((g) => g.folder_ids.includes(node.id));
    return (
      <div key={node.id} className="relative">
        {row(
          node.name,
          node.id,
          <>
            {hasChildren ? (
              <span onClick={(e) => { e.stopPropagation(); toggle(node.id); }} className="cursor-pointer">
                {isOpen ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
              </span>
            ) : (
              <span className="w-[13px]" />
            )}
            <FolderIcon size={14} className="text-amber-500" />
            {restricted.has(node.id) && <Lock size={10} className="text-slate-400" />}
          </>,
          depth,
          <span className="hidden shrink-0 items-center gap-0.5 group-hover:flex">
            {isAdmin && (
              <button title="Permisos de visibilidad" onClick={() => setPermsFor(permsFor === node.id ? null : node.id)}>
                <Shield size={12} className={restricted.has(node.id) ? "text-[hsl(var(--accent))]" : ""} />
              </button>
            )}
            <button title="Subcarpeta" onClick={() => addFolder(node.id)}><FolderPlus size={13} /></button>
            <button title="Renombrar" onClick={() => {
              const name = window.prompt("Nuevo nombre:", node.name)?.trim();
              if (name) updateM.mutate({ id: node.id, name });
            }}><Pencil size={12} /></button>
            <button title="Borrar" onClick={() => {
              if (window.confirm(`Borrar la carpeta "${node.name}"? Su contenido sube al nivel superior.`))
                deleteM.mutate(node.id);
            }}><Trash2 size={12} className="text-red-500" /></button>
          </span>,
          node.id,
        )}
        {permsFor === node.id && (
          <div className="absolute right-0 z-30 mt-1 w-52 rounded-lg border bg-[hsl(var(--bg))] p-2 shadow-lg">
            <p className="mb-1 px-1 text-xs text-[hsl(var(--muted))]">Grupos que ven esta carpeta (vacío = todos):</p>
            {groups.length === 0 && <p className="px-1 text-xs text-[hsl(var(--muted))]">No hay grupos. Creá grupos en Usuarios.</p>}
            {groups.map((g) => {
              const on = nodeGroups.some((x) => x.id === g.id);
              return (
                <label key={g.id} className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm hover:bg-black/5 dark:hover:bg-white/5">
                  <input type="checkbox" checked={on} onChange={() => {
                    const ids = on ? nodeGroups.filter((x) => x.id !== g.id).map((x) => x.id) : [...nodeGroups.map((x) => x.id), g.id];
                    permM.mutate({ folderId: node.id, ids });
                  }} />
                  {g.name}
                </label>
              );
            })}
            <button className="btn btn-ghost !py-1 mt-1 w-full justify-center" onClick={() => setPermsFor(null)}>Listo</button>
          </div>
        )}
        {isOpen && node.children.map((c) => renderNode(c, depth + 1))}
      </div>
    );
  };

  return (
    <div className="space-y-0.5">
      <div className="flex items-center justify-between px-1.5 pb-1">
        <span className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted))]">Carpetas</span>
        <button title="Nueva carpeta" className="text-[hsl(var(--muted))] hover:text-[hsl(var(--fg))]"
          onClick={() => addFolder(null)}><FolderPlus size={15} /></button>
      </div>
      {row("Todas", ALL, <Layers size={14} className="text-slate-400" />)}
      {row("Sin carpeta", UNFILED, <FolderIcon size={14} className="text-slate-300" />)}
      {tree.map((n) => renderNode(n, 0))}
    </div>
  );
}

// Folder id + all its descendants, for filtering items in a folder subtree.
export function descendants(folders: Folder[], id: string): Set<string> {
  const out = new Set<string>([id]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const f of folders) {
      if (f.parent_id && out.has(f.parent_id) && !out.has(f.id)) {
        out.add(f.id);
        changed = true;
      }
    }
  }
  return out;
}

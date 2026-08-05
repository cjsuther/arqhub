import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ChevronRight, Folder as FolderIcon, FolderPlus, Layers, Pencil, Trash2 } from "lucide-react";
import { useState, type DragEvent, type ReactNode } from "react";

import { api } from "../lib/api";
import type { Folder } from "../lib/types";

export const ALL = null; // show everything
export const UNFILED = "__unfiled__"; // items with no folder

interface Props {
  scope: "element" | "view";
  selected: string | null;
  onSelect: (id: string | null) => void;
  onDropItem?: (folderId: string | null, itemIds: string[]) => void; // drag item(s) onto folder
}

export const DND_ITEM = "application/arqhub-item";

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

// Remember which folders are open across refreshes (per scope, in localStorage).
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
  const [expanded, setExpanded] = useState<Set<string>>(() => loadExpanded(scope));

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

  const tree = buildTree(folders.data ?? []);

  function toggle(id: string) {
    setExpanded((p) => {
      const n = new Set(p);
      n.has(id) ? n.delete(id) : n.add(id);
      try {
        localStorage.setItem(EXPANDED_KEY(scope), JSON.stringify([...n]));
      } catch {
        /* ignore quota/availability errors */
      }
      return n;
    });
  }

  function addFolder(parentId: string | null) {
    const name = window.prompt("Nombre de la carpeta:")?.trim();
    if (name) createM.mutate({ name, scope, parent_id: parentId });
  }

  const droppable = (id: string | null) =>
    onDropItem && id !== ALL
      ? {
          onDragOver: (e: DragEvent) => {
            if (e.dataTransfer.types.includes(DND_ITEM)) e.preventDefault();
          },
          onDrop: (e: DragEvent) => {
            const items = e.dataTransfer.getData(DND_ITEM).split(",").filter(Boolean);
            if (items.length) onDropItem(id === UNFILED ? null : id, items);
          },
        }
      : {};

  const row = (label: string, id: string | null, icon: ReactNode, depth = 0, extra?: ReactNode) => (
    <div
      {...droppable(id)}
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
    return (
      <div key={node.id}>
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
          </>,
          depth,
          <span className="hidden shrink-0 items-center gap-0.5 group-hover:flex">
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

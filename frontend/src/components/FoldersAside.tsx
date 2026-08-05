// Collapsible sidebar wrapper around FolderTree — remembers collapsed state.
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { useState } from "react";

import { FolderTree } from "./FolderTree";

interface Props {
  scope: "element" | "view";
  selected: string | null;
  onSelect: (id: string | null) => void;
  onDropItem?: (folderId: string | null, itemIds: string[]) => void;
}

export function FoldersAside({ scope, selected, onSelect, onDropItem }: Props) {
  const key = `arqhub:folders:${scope}:collapsed`;
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(key) === "1");
  const toggle = () => setCollapsed((c) => { const n = !c; localStorage.setItem(key, n ? "1" : "0"); return n; });

  if (collapsed) {
    return (
      <aside className="surface flex w-10 shrink-0 flex-col items-center rounded-lg border p-1">
        <button title="Mostrar carpetas" className="rounded p-1.5 hover:bg-black/5 dark:hover:bg-white/5" onClick={toggle}>
          <PanelLeftOpen size={18} />
        </button>
      </aside>
    );
  }
  return (
    <aside className="surface w-56 shrink-0 overflow-auto rounded-lg border p-2">
      <div className="flex justify-end">
        <button title="Ocultar carpetas" className="rounded p-1 text-[hsl(var(--muted))] hover:bg-black/5 dark:hover:bg-white/5" onClick={toggle}>
          <PanelLeftClose size={16} />
        </button>
      </div>
      <FolderTree scope={scope} selected={selected} onSelect={onSelect} onDropItem={onDropItem} />
    </aside>
  );
}

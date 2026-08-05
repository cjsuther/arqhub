// A dropdown to file an element or a view into a folder (explicit alternative to
// dragging onto the folder tree). Shows the hierarchy with indentation.
import { useQuery } from "@tanstack/react-query";

import { api } from "../lib/api";
import type { Folder } from "../lib/types";

function flatten(folders: Folder[], parent: string | null = null, depth = 0): { id: string; label: string }[] {
  return folders
    .filter((f) => f.parent_id === parent)
    .sort((a, b) => a.name.localeCompare(b.name))
    .flatMap((f) => [
      { id: f.id, label: `${"— ".repeat(depth)}${f.name}` },
      ...flatten(folders, f.id, depth + 1),
    ]);
}

interface Props {
  scope: "element" | "view";
  value: string | null;
  onChange: (folderId: string | null) => void;
  className?: string;
}

export function FolderSelect({ scope, value, onChange, className }: Props) {
  const folders = useQuery({ queryKey: ["folders", scope], queryFn: () => api.listFolders(scope) });
  const options = flatten(folders.data ?? []);
  return (
    <select className={className ?? "input"} value={value ?? ""}
      onChange={(e) => onChange(e.target.value || null)} title="Carpeta">
      <option value="">Sin carpeta</option>
      {options.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
    </select>
  );
}

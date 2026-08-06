// Reusable user selector with search — single or multiple. Used for the "user"/
// "users" custom fields and every user picker in the app (approvers, mentions,
// draft sharing, group members).
import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useState } from "react";

import { api } from "../lib/api";

interface Props {
  value: string[] | string | null;
  multiple?: boolean;
  onChange: (v: string[] | string | null) => void;
  placeholder?: string;
}

export function UserPicker({ value, multiple, onChange, placeholder = "Buscar usuario…" }: Props) {
  const users = useQuery({ queryKey: ["users"], queryFn: () => api.listUsers() });
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);

  const selected = multiple ? ((value as string[]) ?? []) : value ? [value as string] : [];
  const nameOf = (id: string) => users.data?.find((u) => u.id === id)?.display_name ?? id;
  const matches = (users.data ?? []).filter(
    (u) => !selected.includes(u.id) && `${u.display_name} ${u.email}`.toLowerCase().includes(q.toLowerCase()),
  );

  const add = (id: string) => {
    if (multiple) onChange([...(selected), id]);
    else { onChange(id); setOpen(false); }
    setQ("");
  };
  const remove = (id: string) => {
    if (multiple) onChange(selected.filter((x) => x !== id));
    else onChange(null);
  };

  return (
    <div className="relative">
      {open && <div className="fixed inset-0 z-20" onClick={() => setOpen(false)} />}
      <div className="input flex min-h-9 flex-wrap items-center gap-1 py-1">
        {selected.map((id) => (
          <span key={id} className="flex items-center gap-1 rounded-full bg-[hsl(var(--accent))]/15 px-2 py-0.5 text-xs text-[hsl(var(--accent))]">
            {nameOf(id)}
            <button onClick={() => remove(id)}><X size={11} /></button>
          </span>
        ))}
        <input
          className="min-w-24 flex-1 bg-transparent text-sm outline-none"
          placeholder={selected.length && !multiple ? "" : placeholder}
          value={q}
          onChange={(e) => { setQ(e.target.value); setOpen(true); }}
          onFocus={() => setOpen(true)}
        />
      </div>
      {open && (
        <div className="absolute z-30 mt-1 max-h-52 w-full overflow-auto rounded-lg border bg-[hsl(var(--bg))] py-1 shadow-lg">
          {matches.slice(0, 50).map((u) => (
            <button key={u.id} className="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm hover:bg-black/5 dark:hover:bg-white/5"
              onClick={() => add(u.id)}>
              <span className="flex-1 truncate">{u.display_name}</span>
              <span className="text-xs text-[hsl(var(--muted))]">{u.email}</span>
            </button>
          ))}
          {matches.length === 0 && <p className="px-3 py-2 text-xs text-[hsl(var(--muted))]">Sin coincidencias.</p>}
        </div>
      )}
    </div>
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, X } from "lucide-react";
import { useState } from "react";

import { api } from "../../lib/api";
import type { Group } from "../../lib/types";

interface Props {
  group: Group;
  onClose: () => void;
}

// Manage a group's members from the group side (pick users).
export function GroupMembersDialog({ group, onClose }: Props) {
  const qc = useQueryClient();
  const users = useQuery({ queryKey: ["users"], queryFn: () => api.listUsers() });
  const [q, setQ] = useState("");

  const set = useMutation({
    mutationFn: (ids: string[]) => api.setGroupMembers(group.id, ids),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["groups"] });
      qc.invalidateQueries({ queryKey: ["users"] });
    },
  });

  const current = new Set(set.data?.user_ids ?? group.user_ids);
  const visible = (users.data ?? []).filter(
    (u) => `${u.display_name} ${u.email}`.toLowerCase().includes(q.toLowerCase()),
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="surface flex max-h-[80vh] w-full max-w-md flex-col rounded-xl border shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="font-semibold">Miembros de «{group.name}»</h2>
          <button className="btn btn-ghost !p-1" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="border-b p-3">
          <div className="relative">
            <Search size={15} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--muted))]" />
            <input className="input w-full pl-8" placeholder="Buscar usuario…" value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-auto p-2">
          {visible.map((u) => {
            const on = current.has(u.id);
            return (
              <label key={u.id} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-black/5 dark:hover:bg-white/5">
                <input type="checkbox" checked={on} onChange={() => {
                  const ids = on ? [...current].filter((x) => x !== u.id) : [...current, u.id];
                  set.mutate(ids);
                }} />
                <span className="flex-1 truncate">{u.display_name}</span>
                <span className="text-xs text-[hsl(var(--muted))]">{u.email}</span>
              </label>
            );
          })}
        </div>
        <div className="border-t px-4 py-2 text-xs text-[hsl(var(--muted))]">{current.size} miembro(s)</div>
      </div>
    </div>
  );
}

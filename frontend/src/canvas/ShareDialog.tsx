import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";

import { api } from "../lib/api";

interface Props {
  slug: string;
  authorId: string | null;
  onClose: () => void;
}

// Pick which users can see this draft (beyond its author). SPEC §12.
export function ShareDialog({ slug, authorId, onClose }: Props) {
  const qc = useQueryClient();
  const users = useQuery({ queryKey: ["users"], queryFn: () => api.listUsers() });
  const shares = useQuery({ queryKey: ["shares", slug], queryFn: () => api.getViewShares(slug) });

  const set = useMutation({
    mutationFn: (ids: string[]) => api.setViewShares(slug, ids),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["shares", slug] }); qc.invalidateQueries({ queryKey: ["views"] }); },
  });

  const current = new Set(shares.data ?? []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="surface flex max-h-[80vh] w-full max-w-md flex-col rounded-xl border shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="font-semibold">Compartir borrador</h2>
          <button className="btn btn-ghost !p-1" onClick={onClose}><X size={18} /></button>
        </div>
        <p className="px-4 pt-3 text-xs text-[hsl(var(--muted))]">
          Un borrador solo lo ve su autor. Elegí quién más puede verlo.
        </p>
        <div className="min-h-0 flex-1 overflow-auto p-3">
          {users.data?.filter((u) => u.id !== authorId).map((u) => {
            const on = current.has(u.id);
            return (
              <label key={u.id} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-black/5 dark:hover:bg-white/5">
                <input type="checkbox" checked={on} onChange={() => {
                  const ids = on ? [...current].filter((x) => x !== u.id) : [...current, u.id];
                  set.mutate(ids);
                }} />
                <span className="flex-1">{u.display_name}</span>
                <span className="text-xs text-[hsl(var(--muted))]">{u.email}</span>
              </label>
            );
          })}
        </div>
      </div>
    </div>
  );
}

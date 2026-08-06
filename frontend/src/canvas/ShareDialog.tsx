import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";

import { UserPicker } from "../components/UserPicker";
import { api } from "../lib/api";

interface Props {
  slug: string;
  authorId: string | null;
  onClose: () => void;
}

// Pick which users can see this draft (beyond its author). SPEC §12.
export function ShareDialog({ slug, authorId, onClose }: Props) {
  const qc = useQueryClient();
  const shares = useQuery({ queryKey: ["shares", slug], queryFn: () => api.getViewShares(slug) });

  const set = useMutation({
    mutationFn: (ids: string[]) => api.setViewShares(slug, ids),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["shares", slug] }); qc.invalidateQueries({ queryKey: ["views"] }); },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="surface w-full max-w-md rounded-xl border shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="font-semibold">Compartir borrador</h2>
          <button className="btn btn-ghost !p-1" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="p-4">
          <p className="mb-2 text-xs text-[hsl(var(--muted))]">
            Un borrador solo lo ve su autor. Buscá y elegí quién más puede verlo.
          </p>
          <UserPicker
            multiple
            value={(shares.data ?? []).filter((id) => id !== authorId)}
            onChange={(ids) => set.mutate((ids as string[]).filter((id) => id !== authorId))}
            placeholder="Buscar usuario para compartir…"
          />
        </div>
      </div>
    </div>
  );
}

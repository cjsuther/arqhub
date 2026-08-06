import { useQuery } from "@tanstack/react-query";
import { Plus, Search, X } from "lucide-react";
import { useState } from "react";

import { api } from "../lib/api";

interface Props {
  onSubmit: (approvers: string[], comment: string) => void;
  onCancel: () => void;
  busy?: boolean;
}

export function SubmitReviewModal({ onSubmit, onCancel, busy }: Props) {
  const users = useQuery({ queryKey: ["users"], queryFn: () => api.listUsers() });
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [extra, setExtra] = useState("");
  const [comment, setComment] = useState("");
  const [q, setQ] = useState("");

  // Only approver-eligible users can approve (SPEC §12).
  const candidates = (users.data ?? [])
    .filter((u) => u.role === "approver" || u.role === "admin")
    .filter((u) => `${u.display_name} ${u.email}`.toLowerCase().includes(q.toLowerCase()));
  const externals = extra
    .split(/[,;\s]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  const approvers = Array.from(new Set([...selected, ...externals]));

  function toggle(email: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(email) ? next.delete(email) : next.add(email);
      return next;
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onCancel}>
      <div className="surface w-96 rounded-lg border p-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Enviar a revisión</h3>
          <button className="btn btn-ghost !border-transparent !p-1" onClick={onCancel}><X size={16} /></button>
        </div>
        <p className="mt-1 text-sm text-[hsl(var(--muted))]">Elegí quién debe aprobar esta vista.</p>

        <div className="relative mt-3">
          <Search size={15} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[hsl(var(--muted))]" />
          <input className="input w-full pl-8 text-sm" placeholder="Buscar aprobador…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>

        <div className="mt-2 max-h-48 space-y-1 overflow-auto">
          {candidates.map((u) => (
            <label key={u.id} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-black/5 dark:hover:bg-white/5">
              <input type="checkbox" checked={selected.has(u.email)} onChange={() => toggle(u.email)} />
              <span className="flex-1">{u.display_name}</span>
              <span className="text-xs text-[hsl(var(--muted))]">{u.email}</span>
              <span className="badge bg-black/5 dark:bg-white/10">{u.role}</span>
            </label>
          ))}
          {candidates.length === 0 && !users.isLoading && (
            <p className="px-2 py-2 text-xs text-[hsl(var(--muted))]">No hay aprobadores; agregá un email abajo.</p>
          )}
        </div>

        <label className="mt-3 block text-xs font-medium text-[hsl(var(--muted))]">Otros emails (opcional)</label>
        <input className="input mt-1 w-full text-sm" placeholder="externo@correo.com, otro@correo.com"
          value={extra} onChange={(e) => setExtra(e.target.value)} />

        <label className="mt-3 block text-xs font-medium text-[hsl(var(--muted))]">Comentario (opcional)</label>
        <textarea className="input mt-1 min-h-16 w-full resize-y text-sm" value={comment}
          onChange={(e) => setComment(e.target.value)} placeholder="Contexto para los aprobadores…" />

        <div className="mt-4 flex items-center justify-between">
          <span className="text-xs text-[hsl(var(--muted))]">{approvers.length} aprobador(es)</span>
          <div className="flex gap-2">
            <button className="btn btn-ghost" onClick={onCancel}>Cancelar</button>
            <button className="btn btn-primary disabled:opacity-40" disabled={busy || approvers.length === 0}
              onClick={() => onSubmit(approvers, comment)}>
              <Plus size={15} /> Enviar
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

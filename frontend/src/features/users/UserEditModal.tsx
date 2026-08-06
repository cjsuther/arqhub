import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useState } from "react";

import { api } from "../../lib/api";
import type { Group, Role, User } from "../../lib/types";

const ROLES: { value: Role; label: string }[] = [
  { value: "viewer", label: "Lector" },
  { value: "editor", label: "Editor" },
  { value: "approver", label: "Aprobador" },
  { value: "admin", label: "Administrador" },
];

interface Props {
  user: User;
  groups: Group[];
  onClose: () => void;
}

export function UserEditModal({ user, groups, onClose }: Props) {
  const qc = useQueryClient();
  const [name, setName] = useState(user.display_name);
  const [email, setEmail] = useState(user.email);
  const [role, setRole] = useState<Role>(user.role);
  const [groupIds, setGroupIds] = useState<string[]>(user.groups.map((g) => g.id));
  const [error, setError] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: async () => {
      await api.updateUser(user.id, { display_name: name, email, role });
      await api.setUserGroups(user.id, groupIds);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      qc.invalidateQueries({ queryKey: ["groups"] });
      qc.invalidateQueries({ queryKey: ["me"] });
      onClose();
    },
    onError: (e) => setError(e instanceof Error ? clean(e.message) : "Error"),
  });

  const toggle = (id: string) =>
    setGroupIds((g) => (g.includes(id) ? g.filter((x) => x !== id) : [...g, id]));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="surface flex max-h-[85vh] w-full max-w-md flex-col rounded-xl border shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="font-semibold">Editar usuario</h2>
          <button className="btn btn-ghost !p-1" onClick={onClose}><X size={18} /></button>
        </div>
        <div className="min-h-0 flex-1 space-y-3 overflow-auto p-4">
          {error && <p className="rounded bg-red-500/10 px-3 py-2 text-sm text-red-600">{error}</p>}
          <div>
            <label className="text-xs text-[hsl(var(--muted))]">Nombre</label>
            <input className="input w-full" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-[hsl(var(--muted))]">Email</label>
            <input className="input w-full" value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="text-xs text-[hsl(var(--muted))]">Rol</label>
            <select className="input w-full" value={role} onChange={(e) => setRole(e.target.value as Role)}>
              {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs text-[hsl(var(--muted))]">Grupos</label>
            <div className="mt-1 space-y-0.5 rounded-lg border p-2">
              {groups.length === 0 && <p className="px-1 text-xs text-[hsl(var(--muted))]">No hay grupos.</p>}
              {groups.map((g) => (
                <label key={g.id} className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm hover:bg-black/5 dark:hover:bg-white/5">
                  <input type="checkbox" checked={groupIds.includes(g.id)} onChange={() => toggle(g.id)} />
                  {g.name}
                </label>
              ))}
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 border-t px-4 py-3">
          <button className="btn btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary" disabled={save.isPending || !email.trim() || !name.trim()} onClick={() => save.mutate()}>
            {save.isPending ? "Guardando…" : "Guardar"}
          </button>
        </div>
      </div>
    </div>
  );
}

function clean(msg: string): string {
  const m = msg.match(/"detail":"([^"]+)"/) || msg.match(/:\s*(.+)$/);
  return m ? m[1] : msg;
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Info, ShieldAlert, Trash2, UserPlus } from "lucide-react";
import { useState } from "react";

import { api } from "../../lib/api";
import type { Role } from "../../lib/types";

const ROLES: { value: Role; label: string }[] = [
  { value: "viewer", label: "Lector" },
  { value: "editor", label: "Editor" },
  { value: "approver", label: "Aprobador" },
  { value: "admin", label: "Administrador" },
];

export function UsersPage() {
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: api.getMe });
  const usersQ = useQuery({ queryKey: ["users"], queryFn: () => api.listUsers() });

  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [error, setError] = useState<string | null>(null);

  const invalidate = () => qc.invalidateQueries({ queryKey: ["users"] });
  const onErr = (e: unknown) => setError(e instanceof Error ? cleanError(e.message) : "Error");

  const create = useMutation({
    mutationFn: () => api.createUser({ email, display_name: name || email, role }),
    onSuccess: () => { setEmail(""); setName(""); setRole("viewer"); setError(null); invalidate(); },
    onError: onErr,
  });
  const changeRole = useMutation({
    mutationFn: (v: { id: string; role: string }) => api.updateUser(v.id, { role: v.role }),
    onSuccess: () => { setError(null); invalidate(); }, onError: onErr,
  });
  const remove = useMutation({
    mutationFn: (id: string) => api.deleteUser(id),
    onSuccess: () => { setError(null); invalidate(); }, onError: onErr,
  });

  if (me.data && me.data.role !== "admin") {
    return (
      <div className="mx-auto max-w-lg rounded-lg border p-6 text-center text-sm text-[hsl(var(--muted))]">
        <ShieldAlert className="mx-auto mb-2 text-amber-500" />
        Necesitás el rol <strong>Administrador</strong> para gestionar usuarios.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Usuarios y accesos</h1>
        <p className="text-sm text-[hsl(var(--muted))]">Alta de usuarios locales y asignación de roles.</p>
      </div>

      <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs">
        <Info size={15} className="mt-0.5 shrink-0 text-amber-600" />
        <span>
          Los usuarios provenientes de <strong>Entra ID</strong> se marcan como tales: su rol se
          <strong> re-sincroniza en cada login</strong>, así que un cambio manual actúa como override temporal.
          Para ellos, la fuente de verdad son los app-roles/grupos de Entra.
        </span>
      </div>

      {error && <p className="rounded bg-red-500/10 px-3 py-2 text-sm text-red-600">{error}</p>}

      <div className="surface flex flex-wrap items-end gap-2 rounded-lg border p-4">
        <div className="flex-1 min-w-40">
          <label className="text-xs text-[hsl(var(--muted))]">Email</label>
          <input className="input w-full" placeholder="persona@empresa.com" value={email}
            onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="flex-1 min-w-40">
          <label className="text-xs text-[hsl(var(--muted))]">Nombre</label>
          <input className="input w-full" placeholder="Nombre y apellido" value={name}
            onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-[hsl(var(--muted))]">Rol</label>
          <select className="input" value={role} onChange={(e) => setRole(e.target.value as Role)}>
            {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </div>
        <button className="btn btn-primary" disabled={!email.trim() || create.isPending}
          onClick={() => create.mutate()}>
          <UserPlus size={16} /> Agregar
        </button>
      </div>

      <div className="surface overflow-hidden rounded-lg border">
        <table className="w-full text-sm">
          <thead className="border-b text-left text-xs uppercase text-[hsl(var(--muted))]">
            <tr>
              <th className="px-4 py-2 font-medium">Usuario</th>
              <th className="px-4 py-2 font-medium">Origen</th>
              <th className="px-4 py-2 font-medium">Rol</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {usersQ.data?.map((u) => (
              <tr key={u.id} className="border-b last:border-0">
                <td className="px-4 py-2">
                  <div className="font-medium">{u.display_name}{me.data?.id === u.id && <span className="ml-1 text-xs text-[hsl(var(--muted))]">(vos)</span>}</div>
                  <div className="text-xs text-[hsl(var(--muted))]">{u.email}</div>
                </td>
                <td className="px-4 py-2">
                  <span className="badge bg-black/5 dark:bg-white/10">{u.is_entra ? "Entra ID" : "Local"}</span>
                </td>
                <td className="px-4 py-2">
                  <select className="input !py-1" value={u.role}
                    onChange={(e) => changeRole.mutate({ id: u.id, role: e.target.value })}>
                    {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                  </select>
                </td>
                <td className="px-4 py-2 text-right">
                  {me.data?.id !== u.id && (
                    <button className="btn btn-ghost !py-1 text-red-600" title="Eliminar"
                      onClick={() => { if (window.confirm(`¿Eliminar a ${u.display_name}?`)) remove.mutate(u.id); }}>
                      <Trash2 size={14} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {usersQ.data?.length === 0 && (
          <p className="px-4 py-6 text-center text-sm text-[hsl(var(--muted))]">No hay usuarios.</p>
        )}
      </div>
    </div>
  );
}

// The API returns "409 Conflict: {"detail":"…"}" — surface just the human message.
function cleanError(msg: string): string {
  const m = msg.match(/"detail":"([^"]+)"/) || msg.match(/:\s*(.+)$/);
  return m ? m[1] : msg;
}

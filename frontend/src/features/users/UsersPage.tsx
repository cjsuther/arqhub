import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Info, Pencil, Plus, ShieldAlert, Trash2, UserPlus, Users2 } from "lucide-react";
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
  const groupsQ = useQuery({ queryKey: ["groups"], queryFn: () => api.listGroups() });

  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [newGroup, setNewGroup] = useState("");
  const [openGroups, setOpenGroups] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const invUsers = () => qc.invalidateQueries({ queryKey: ["users"] });
  const invGroups = () => { qc.invalidateQueries({ queryKey: ["groups"] }); qc.invalidateQueries({ queryKey: ["users"] }); };
  const onErr = (e: unknown) => setError(e instanceof Error ? cleanError(e.message) : "Error");
  const ok = () => setError(null);

  const create = useMutation({
    mutationFn: () => api.createUser({ email, display_name: name || email, role }),
    onSuccess: () => { setEmail(""); setName(""); setRole("viewer"); ok(); invUsers(); }, onError: onErr,
  });
  const updUser = useMutation({
    mutationFn: (v: { id: string; role?: string; display_name?: string }) => api.updateUser(v.id, v),
    onSuccess: () => { ok(); invUsers(); }, onError: onErr,
  });
  const removeUser = useMutation({ mutationFn: (id: string) => api.deleteUser(id), onSuccess: () => { ok(); invUsers(); }, onError: onErr });
  const setGroups = useMutation({
    mutationFn: (v: { id: string; ids: string[] }) => api.setUserGroups(v.id, v.ids),
    onSuccess: () => { ok(); invUsers(); }, onError: onErr,
  });

  const addGroup = useMutation({ mutationFn: () => api.createGroup(newGroup.trim()), onSuccess: () => { setNewGroup(""); ok(); invGroups(); }, onError: onErr });
  const renGroup = useMutation({ mutationFn: (v: { id: string; name: string }) => api.updateGroup(v.id, v.name), onSuccess: () => { ok(); invGroups(); }, onError: onErr });
  const delGroup = useMutation({ mutationFn: (id: string) => api.deleteGroup(id), onSuccess: () => { ok(); invGroups(); }, onError: onErr });

  if (me.data && me.data.role !== "admin") {
    return (
      <div className="mx-auto max-w-lg rounded-lg border p-6 text-center text-sm text-[hsl(var(--muted))]">
        <ShieldAlert className="mx-auto mb-2 text-amber-500" />
        Necesitás el rol <strong>Administrador</strong> para gestionar usuarios.
      </div>
    );
  }

  const groups = groupsQ.data ?? [];

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Usuarios y accesos</h1>
        <p className="text-sm text-[hsl(var(--muted))]">Usuarios, roles y grupos. Los grupos otorgan visibilidad sobre carpetas.</p>
      </div>

      <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs">
        <Info size={15} className="mt-0.5 shrink-0 text-amber-600" />
        <span>Un usuario puede pertenecer a varios grupos; un grupo puede ver varias carpetas. Los permisos de cada carpeta se editan también desde el árbol del Catálogo/Vistas.</span>
      </div>

      {error && <p className="rounded bg-red-500/10 px-3 py-2 text-sm text-red-600">{error}</p>}

      {/* Groups management */}
      <div className="surface rounded-lg border p-4">
        <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold"><Users2 size={16} /> Grupos</h2>
        <div className="mb-3 flex gap-2">
          <input className="input flex-1" placeholder="Nombre del grupo (ej: Arquitectura)" value={newGroup}
            onChange={(e) => setNewGroup(e.target.value)} onKeyDown={(e) => e.key === "Enter" && newGroup.trim() && addGroup.mutate()} />
          <button className="btn btn-primary" disabled={!newGroup.trim() || addGroup.isPending} onClick={() => addGroup.mutate()}>
            <Plus size={15} /> Crear grupo
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {groups.map((g) => (
            <span key={g.id} className="group flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm">
              {g.name} <span className="text-xs text-[hsl(var(--muted))]">· {g.member_count}</span>
              <button title="Renombrar" onClick={() => { const n = window.prompt("Nuevo nombre:", g.name)?.trim(); if (n) renGroup.mutate({ id: g.id, name: n }); }}>
                <Pencil size={12} />
              </button>
              <button title="Borrar" onClick={() => window.confirm(`¿Borrar el grupo "${g.name}"?`) && delGroup.mutate(g.id)}>
                <Trash2 size={12} className="text-red-500" />
              </button>
            </span>
          ))}
          {groups.length === 0 && <span className="text-sm text-[hsl(var(--muted))]">Sin grupos todavía.</span>}
        </div>
      </div>

      {/* Create user */}
      <div className="surface flex flex-wrap items-end gap-2 rounded-lg border p-4">
        <div className="flex-1 min-w-40">
          <label className="text-xs text-[hsl(var(--muted))]">Email</label>
          <input className="input w-full" placeholder="persona@empresa.com" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="flex-1 min-w-40">
          <label className="text-xs text-[hsl(var(--muted))]">Nombre</label>
          <input className="input w-full" placeholder="Nombre y apellido" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <label className="text-xs text-[hsl(var(--muted))]">Rol</label>
          <select className="input" value={role} onChange={(e) => setRole(e.target.value as Role)}>
            {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </div>
        <button className="btn btn-primary" disabled={!email.trim() || create.isPending} onClick={() => create.mutate()}>
          <UserPlus size={16} /> Agregar
        </button>
      </div>

      {/* Users table */}
      <div className="surface overflow-visible rounded-lg border">
        <table className="w-full text-sm">
          <thead className="border-b text-left text-xs uppercase text-[hsl(var(--muted))]">
            <tr>
              <th className="px-4 py-2 font-medium">Usuario</th>
              <th className="px-4 py-2 font-medium">Rol</th>
              <th className="px-4 py-2 font-medium">Grupos</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {usersQ.data?.map((u) => (
              <tr key={u.id} className="border-b last:border-0">
                <td className="px-4 py-2">
                  <div className="flex items-center gap-1.5 font-medium">
                    {u.display_name}
                    {me.data?.id === u.id && <span className="text-xs text-[hsl(var(--muted))]">(vos)</span>}
                    <button title="Editar nombre" className="text-[hsl(var(--muted))] hover:text-[hsl(var(--fg))]"
                      onClick={() => { const n = window.prompt("Nombre:", u.display_name)?.trim(); if (n) updUser.mutate({ id: u.id, display_name: n }); }}>
                      <Pencil size={12} />
                    </button>
                  </div>
                  <div className="text-xs text-[hsl(var(--muted))]">{u.email} · {u.is_entra ? "Entra ID" : "Local"}</div>
                </td>
                <td className="px-4 py-2">
                  <select className="input !py-1" value={u.role} onChange={(e) => updUser.mutate({ id: u.id, role: e.target.value })}>
                    {ROLES.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                  </select>
                </td>
                <td className="relative px-4 py-2">
                  <button className="btn btn-ghost !py-1" onClick={() => setOpenGroups(openGroups === u.id ? null : u.id)}>
                    {u.groups.length ? u.groups.map((g) => g.name).join(", ") : "—"} <span className="text-xs">▾</span>
                  </button>
                  {openGroups === u.id && (
                    <div className="absolute z-20 mt-1 w-56 rounded-lg border bg-[hsl(var(--bg))] p-2 shadow-lg">
                      {groups.length === 0 && <p className="p-2 text-xs text-[hsl(var(--muted))]">Creá grupos primero.</p>}
                      {groups.map((g) => {
                        const inG = u.groups.some((x) => x.id === g.id);
                        return (
                          <label key={g.id} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm hover:bg-black/5 dark:hover:bg-white/5">
                            <input type="checkbox" checked={inG} onChange={() => {
                              const ids = inG ? u.groups.filter((x) => x.id !== g.id).map((x) => x.id) : [...u.groups.map((x) => x.id), g.id];
                              setGroups.mutate({ id: u.id, ids });
                            }} />
                            {g.name}
                          </label>
                        );
                      })}
                      <button className="btn btn-ghost !py-1 mt-1 w-full justify-center" onClick={() => setOpenGroups(null)}>Listo</button>
                    </div>
                  )}
                </td>
                <td className="px-4 py-2 text-right">
                  {me.data?.id !== u.id && (
                    <button className="btn btn-ghost !py-1 text-red-600" title="Eliminar"
                      onClick={() => window.confirm(`¿Eliminar a ${u.display_name}?`) && removeUser.mutate(u.id)}>
                      <Trash2 size={14} />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function cleanError(msg: string): string {
  const m = msg.match(/"detail":"([^"]+)"/) || msg.match(/:\s*(.+)$/);
  return m ? m[1] : msg;
}

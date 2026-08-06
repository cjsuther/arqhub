import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, KeyRound, Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { api } from "../../lib/api";
import { formatDate } from "../../lib/ui";

export function ProfilePage() {
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: api.getMe });
  const tokens = useQuery({ queryKey: ["tokens"], queryFn: () => api.listTokens() });
  const [name, setName] = useState("");
  const [fresh, setFresh] = useState<string | null>(null);

  const invalidate = () => qc.invalidateQueries({ queryKey: ["tokens"] });
  const create = useMutation({
    mutationFn: () => api.createToken(name.trim() || "MCP"),
    onSuccess: (t) => { setFresh(t.token); setName(""); invalidate(); },
  });
  const revoke = useMutation({ mutationFn: (id: string) => api.revokeToken(id), onSuccess: invalidate });

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Mi perfil</h1>
        {me.data && <p className="text-sm text-[hsl(var(--muted))]">{me.data.display_name} · {me.data.email}</p>}
      </div>

      <div className="surface rounded-lg border p-4">
        <h2 className="mb-1 flex items-center gap-2 text-sm font-semibold"><KeyRound size={16} /> Tokens de acceso (MCP)</h2>
        <p className="mb-3 text-xs text-[hsl(var(--muted))]">
          Un token autentica el servidor MCP (o scripts) como vos. Se muestra una sola vez: guardalo.
        </p>

        <div className="mb-3 flex gap-2">
          <input className="input flex-1" placeholder="Nombre del token (ej: MCP en mi PC)" value={name}
            onChange={(e) => setName(e.target.value)} onKeyDown={(e) => e.key === "Enter" && create.mutate()} />
          <button className="btn btn-primary" disabled={create.isPending} onClick={() => create.mutate()}>
            <Plus size={15} /> Generar token
          </button>
        </div>

        {fresh && (
          <div className="mb-3 rounded-lg border border-green-500/40 bg-green-500/10 p-3 text-sm">
            <p className="mb-1 font-medium text-green-700 dark:text-green-400">Token nuevo (copialo ahora, no se vuelve a mostrar):</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 break-all rounded bg-black/10 px-2 py-1 text-xs dark:bg-white/10">{fresh}</code>
              <button className="btn btn-ghost !py-1" onClick={() => navigator.clipboard.writeText(fresh).catch(() => {})}>
                <Copy size={14} /> Copiar
              </button>
            </div>
          </div>
        )}

        <div className="divide-y rounded-lg border">
          {tokens.data?.map((t) => (
            <div key={t.id} className="flex items-center gap-2 px-3 py-2 text-sm">
              <span className="font-medium">{t.name}</span>
              <code className="text-xs text-[hsl(var(--muted))]">{t.prefix}</code>
              <span className="ml-auto text-xs text-[hsl(var(--muted))]">
                {t.last_used_at ? `usado ${formatDate(t.last_used_at)}` : "sin uso"} · creado {formatDate(t.created_at)}
              </span>
              <button className="text-red-500" title="Revocar" onClick={() => window.confirm(`¿Revocar «${t.name}»?`) && revoke.mutate(t.id)}>
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          {tokens.data?.length === 0 && <p className="px-3 py-4 text-center text-xs text-[hsl(var(--muted))]">Todavía no generaste tokens.</p>}
        </div>
      </div>

      <div className="surface rounded-lg border p-4 text-sm">
        <h2 className="mb-2 text-sm font-semibold">Configurar el MCP</h2>
        <p className="mb-2 text-xs text-[hsl(var(--muted))]">Pegá tu token en la config del servidor MCP (variables de entorno):</p>
        <pre className="overflow-x-auto rounded bg-black/10 p-3 text-xs dark:bg-white/10">{`ARQHUB_API=http://localhost:8000/api/v1
ARQHUB_PAT=<tu-token>`}</pre>
        <p className="mt-2 text-xs text-[hsl(var(--muted))]">El MCP hará las llamadas a la API como vos, con tus permisos.</p>
      </div>
    </div>
  );
}

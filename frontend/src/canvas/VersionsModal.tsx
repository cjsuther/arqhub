import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { GitCommitHorizontal, Plus, X } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../lib/api";
import type { EntityDiff, ModelDiff } from "../lib/types";

interface Props {
  slug: string;
  onClose: () => void;
}

function DiffSection({ title, diff }: { title: string; diff: EntityDiff }) {
  const empty = !diff.added.length && !diff.removed.length && !diff.modified.length;
  if (empty) return null;
  return (
    <div className="space-y-1">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-[hsl(var(--muted))]">{title}</h4>
      {diff.added.map((id) => (
        <div key={`a-${id}`} className="rounded bg-green-500/10 px-2 py-1 text-xs text-green-700 dark:text-green-400">
          + agregado: <code>{id}</code>
        </div>
      ))}
      {diff.removed.map((id) => (
        <div key={`r-${id}`} className="rounded bg-red-500/10 px-2 py-1 text-xs text-red-700 dark:text-red-400">
          − eliminado: <code>{id}</code>
        </div>
      ))}
      {diff.modified.map((m) => (
        <div key={`m-${m.id}`} className="rounded bg-amber-500/10 px-2 py-1 text-xs text-amber-800 dark:text-amber-300">
          ~ modificado: <code>{m.id}</code>
          <ul className="mt-0.5 space-y-0.5 pl-4">
            {m.changes.map((c) => (
              <li key={c.field}>
                <span className="font-medium">{c.field}</span>:{" "}
                <span className="line-through opacity-70">{String(c.before ?? "∅")}</span> →{" "}
                <span>{String(c.after ?? "∅")}</span>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

export function VersionsModal({ slug, onClose }: Props) {
  const qc = useQueryClient();
  const versions = useQuery({ queryKey: ["versions", slug], queryFn: () => api.listVersions(slug) });
  const [from, setFrom] = useState<number | null>(null);
  const [to, setTo] = useState<number | null>(null);
  const [message, setMessage] = useState("");

  // Default the comparison to the two most recent versions.
  useEffect(() => {
    const v = versions.data;
    if (v && v.length >= 1 && from === null) {
      setTo(v[v.length - 1].version);
      setFrom(v.length >= 2 ? v[v.length - 2].version : v[v.length - 1].version);
    }
  }, [versions.data, from]);

  const create = useMutation({
    mutationFn: () => api.createVersion(slug, message.trim() || "Sin descripción"),
    onSuccess: () => {
      setMessage("");
      qc.invalidateQueries({ queryKey: ["versions", slug] });
      qc.invalidateQueries({ queryKey: ["view-graph", slug] });
    },
  });

  const diff = useQuery({
    queryKey: ["diff", slug, from, to],
    queryFn: () => api.diffVersions(slug, from!, to!),
    enabled: from !== null && to !== null && from !== to,
  });

  const list = versions.data ?? [];
  const noChanges = diff.data && isEmpty(diff.data);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="surface flex max-h-[85vh] w-full max-w-2xl flex-col rounded-xl border shadow-xl"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="flex items-center gap-2 font-semibold"><GitCommitHorizontal size={18} /> Versiones</h2>
          <button className="btn btn-ghost !p-1" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="flex items-end gap-2 border-b px-4 py-3">
          <div className="flex-1">
            <label className="text-xs text-[hsl(var(--muted))]">Guardar versión actual</label>
            <input className="input w-full" placeholder="Descripción del cambio…" value={message}
              onChange={(e) => setMessage(e.target.value)} />
          </div>
          <button className="btn btn-primary" disabled={create.isPending} onClick={() => create.mutate()}>
            <Plus size={15} /> Guardar
          </button>
        </div>

        {list.length === 0 ? (
          <p className="p-6 text-center text-sm text-[hsl(var(--muted))]">
            Aún no hay versiones. Guardá una para empezar a llevar historial.
          </p>
        ) : (
          <>
            <div className="flex items-center gap-3 border-b px-4 py-2 text-sm">
              <label className="flex items-center gap-1">Desde
                <select className="input !py-1" value={from ?? ""} onChange={(e) => setFrom(Number(e.target.value))}>
                  {list.map((v) => <option key={v.version} value={v.version}>v{v.version}</option>)}
                </select>
              </label>
              <label className="flex items-center gap-1">Hasta
                <select className="input !py-1" value={to ?? ""} onChange={(e) => setTo(Number(e.target.value))}>
                  {list.map((v) => <option key={v.version} value={v.version}>v{v.version}</option>)}
                </select>
              </label>
              <span className="ml-auto text-xs text-[hsl(var(--muted))]">{list.length} versiones</span>
            </div>

            <div className="min-h-0 flex-1 space-y-3 overflow-auto p-4">
              <ol className="space-y-1 text-xs">
                {list.map((v) => (
                  <li key={v.version} className="flex gap-2">
                    <span className="font-mono font-semibold">v{v.version}</span>
                    <span className="text-[hsl(var(--muted))]">{v.message}</span>
                  </li>
                ))}
              </ol>
              <div className="border-t pt-3">
                {from === to && <p className="text-sm text-[hsl(var(--muted))]">Elegí dos versiones distintas para comparar.</p>}
                {diff.isLoading && <p className="text-sm text-[hsl(var(--muted))]">Comparando…</p>}
                {noChanges && <p className="text-sm text-[hsl(var(--muted))]">Sin diferencias entre v{from} y v{to}.</p>}
                {diff.data && !noChanges && (
                  <div className="space-y-3">
                    <DiffSection title="Elementos" diff={diff.data.elements} />
                    <DiffSection title="Relaciones" diff={diff.data.relations} />
                    <DiffSection title="Vistas" diff={diff.data.views} />
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function isEmpty(d: ModelDiff): boolean {
  const e = (x: EntityDiff) => !x.added.length && !x.removed.length && !x.modified.length;
  return e(d.elements) && e(d.relations) && e(d.views);
}

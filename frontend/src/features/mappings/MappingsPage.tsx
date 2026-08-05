import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { api } from "../../lib/api";
import { langLabel } from "../../lib/ui";

const LAYERS: { value: string; label: string }[] = [
  { value: "business", label: "Negocio" },
  { value: "application", label: "Aplicación" },
  { value: "technology", label: "Tecnología" },
  { value: "motivation", label: "Motivación" },
  { value: "strategy", label: "Estrategia" },
  { value: "implementation", label: "Implementación" },
  { value: "physical", label: "Física" },
];
const LAYER_LABEL = Object.fromEntries(LAYERS.map((l) => [l.value, l.label]));
const LANGS = ["archimate", "bpmn", "uml"] as const;

export function MappingsPage() {
  const qc = useQueryClient();
  const registry = useQuery({ queryKey: ["registry"], queryFn: api.registry });
  const me = useQuery({ queryKey: ["me"], queryFn: api.getMe });
  const isAdmin = me.data?.role === "admin";

  const [key, setKey] = useState("");
  const [layer, setLayer] = useState("application");
  const [proj, setProj] = useState<Record<string, string>>({ archimate: "", bpmn: "", uml: "" });
  const [error, setError] = useState<string | null>(null);

  const add = useMutation({
    mutationFn: () => api.addKind({
      key, layer, archimate: proj.archimate || null, bpmn: proj.bpmn || null, uml: proj.uml || null,
    }),
    onSuccess: (reg) => {
      qc.setQueryData(["registry"], reg);
      setKey(""); setProj({ archimate: "", bpmn: "", uml: "" }); setError(null);
    },
    onError: (e) => setError(e instanceof Error ? cleanError(e.message) : "Error"),
  });
  const del = useMutation({
    mutationFn: (k: string) => api.deleteKind(k),
    onSuccess: (reg) => qc.setQueryData(["registry"], reg),
  });

  const kinds = Object.entries(registry.data?.kinds ?? {}).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div>
        <h1 className="text-xl font-semibold">Mapeo de componentes</h1>
        <p className="text-sm text-[hsl(var(--muted))]">
          Cómo se representa cada componente en cada lenguaje. Un componente puede existir en un solo lenguaje.
        </p>
      </div>

      {error && <p className="rounded bg-red-500/10 px-3 py-2 text-sm text-red-600">{error}</p>}

      {isAdmin && (
        <div className="surface rounded-lg border p-4">
          <h2 className="mb-2 text-sm font-semibold">Agregar componente</h2>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            <div>
              <label className="text-xs text-[hsl(var(--muted))]">Clave</label>
              <input className="input w-full" placeholder="ej: data-store" value={key} onChange={(e) => setKey(e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-[hsl(var(--muted))]">Capa</label>
              <select className="input w-full" value={layer} onChange={(e) => setLayer(e.target.value)}>
                {LAYERS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
              </select>
            </div>
            {LANGS.map((l) => (
              <div key={l}>
                <label className="text-xs text-[hsl(var(--muted))]">{langLabel(l)}</label>
                <input className="input w-full" placeholder="— (vacío = no aplica)" value={proj[l]}
                  onChange={(e) => setProj((p) => ({ ...p, [l]: e.target.value }))} />
              </div>
            ))}
          </div>
          <div className="mt-2 flex items-center gap-2">
            <button className="btn btn-primary" disabled={!key.trim() || add.isPending} onClick={() => add.mutate()}>
              <Plus size={15} /> Agregar mapeo
            </button>
            <span className="text-xs text-[hsl(var(--muted))]">Completá al menos un lenguaje.</span>
          </div>
        </div>
      )}

      <div className="surface overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">
          <thead className="border-b text-left text-xs uppercase text-[hsl(var(--muted))]">
            <tr>
              <th className="px-4 py-2 font-medium">Componente</th>
              <th className="px-4 py-2 font-medium">Capa</th>
              {LANGS.map((l) => <th key={l} className="px-4 py-2 font-medium">{langLabel(l)}</th>)}
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {kinds.map(([k, def]) => (
              <tr key={k} className="border-b last:border-0">
                <td className="px-4 py-2">
                  <code>{k}</code>
                  {def.custom && <span className="ml-1.5 badge bg-[hsl(var(--accent))]/15 text-[hsl(var(--accent))]">custom</span>}
                </td>
                <td className="px-4 py-2 text-[hsl(var(--muted))]">{LAYER_LABEL[def.layer] ?? def.layer}</td>
                {LANGS.map((l) => (
                  <td key={l} className="px-4 py-2">
                    {def.mappings[l]
                      ? <span>{def.mappings[l]}</span>
                      : <span className="text-[hsl(var(--muted))]">—</span>}
                  </td>
                ))}
                <td className="px-4 py-2 text-right">
                  {isAdmin && def.custom && (
                    <button className="btn btn-ghost !py-1 text-red-600" title="Eliminar componente"
                      onClick={() => window.confirm(`¿Eliminar el componente "${k}"?`) && del.mutate(k)}>
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

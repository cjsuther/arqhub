import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, X } from "lucide-react";
import { useState } from "react";

import { api } from "../../lib/api";

const TYPES: { v: string; l: string }[] = [
  { v: "text", l: "Texto" },
  { v: "longtext", l: "Texto largo" },
  { v: "date", l: "Fecha" },
  { v: "time", l: "Hora" },
  { v: "select", l: "Selección" },
  { v: "multiselect", l: "Selección múltiple" },
  { v: "user", l: "Usuario (único)" },
  { v: "users", l: "Usuarios (múltiple)" },
  { v: "number", l: "Numérico" },
];
const TYPE_LABEL = Object.fromEntries(TYPES.map((t) => [t.v, t.l]));

export function FieldDefsDialog({ kind, onClose }: { kind: string; onClose: () => void }) {
  const qc = useQueryClient();
  const fields = useQuery({ queryKey: ["fields", kind], queryFn: () => api.listFields(kind) });
  const [key, setKey] = useState("");
  const [label, setLabel] = useState("");
  const [type, setType] = useState("text");
  const [options, setOptions] = useState("");
  const [error, setError] = useState<string | null>(null);

  const invalidate = () => { qc.invalidateQueries({ queryKey: ["fields", kind] }); };
  const add = useMutation({
    mutationFn: () => api.createField(kind, {
      key, label: label || key, field_type: type,
      options: type === "select" || type === "multiselect" ? options.split(",").map((o) => o.trim()).filter(Boolean) : [],
    }),
    onSuccess: () => { setKey(""); setLabel(""); setOptions(""); setError(null); invalidate(); },
    onError: (e) => setError(e instanceof Error ? clean(e.message) : "Error"),
  });
  const del = useMutation({ mutationFn: (id: string) => api.deleteField(id), onSuccess: invalidate });

  const needsOptions = type === "select" || type === "multiselect";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" onClick={onClose}>
      <div className="surface flex max-h-[85vh] w-full max-w-lg flex-col rounded-xl border shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="font-semibold">Campos de «{kind}»</h2>
          <button className="btn btn-ghost !p-1" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="space-y-2 border-b p-4">
          {error && <p className="rounded bg-red-500/10 px-3 py-2 text-sm text-red-600">{error}</p>}
          <div className="grid grid-cols-2 gap-2">
            <input className="input" placeholder="Clave (ej: owner-team)" value={key} onChange={(e) => setKey(e.target.value)} />
            <input className="input" placeholder="Etiqueta" value={label} onChange={(e) => setLabel(e.target.value)} />
            <select className="input" value={type} onChange={(e) => setType(e.target.value)}>
              {TYPES.map((t) => <option key={t.v} value={t.v}>{t.l}</option>)}
            </select>
            {needsOptions && <input className="input" placeholder="Opciones (coma)" value={options} onChange={(e) => setOptions(e.target.value)} />}
          </div>
          <button className="btn btn-primary" disabled={!key.trim() || add.isPending} onClick={() => add.mutate()}>
            <Plus size={15} /> Agregar campo
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-auto p-2">
          {fields.data?.map((f) => (
            <div key={f.id} className="group flex items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-black/5 dark:hover:bg-white/5">
              <span className="font-medium">{f.label}</span>
              <code className="text-xs text-[hsl(var(--muted))]">{f.key}</code>
              <span className="badge bg-black/5 dark:bg-white/10">{TYPE_LABEL[f.field_type] ?? f.field_type}</span>
              {f.options.length > 0 && <span className="truncate text-xs text-[hsl(var(--muted))]">{f.options.join(", ")}</span>}
              <button className="ml-auto text-red-500 opacity-0 group-hover:opacity-100" title="Borrar" onClick={() => del.mutate(f.id)}>
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          {fields.data?.length === 0 && <p className="px-2 py-4 text-center text-sm text-[hsl(var(--muted))]">Este tipo no tiene campos personalizados.</p>}
        </div>
      </div>
    </div>
  );
}

function clean(msg: string): string {
  const m = msg.match(/"detail":"([^"]+)"/) || msg.match(/:\s*(.+)$/);
  return m ? m[1] : msg;
}

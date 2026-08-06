import { X } from "lucide-react";
import { useMemo, useState } from "react";

import type { FieldDef } from "../../lib/types";
import { buildQuery, fieldTokenMap, parseQuery, type QueryPart } from "./search";

const LIFECYCLE_LABEL: Record<string, string> = {
  proposed: "Propuesto", active: "Activo", deprecated: "Obsoleto", retired: "Retirado",
};

const isRangeType = (t: FieldDef["field_type"]) => t === "date" || t === "time" || t === "number";
const htmlType = (t: FieldDef["field_type"]) => (t === "date" ? "date" : t === "time" ? "time" : t === "number" ? "number" : "text");

interface Props {
  initialQuery: string;
  fields: FieldDef[];
  kinds: string[];
  lifecycles: string[];
  onApply: (query: string) => void;
  onClose: () => void;
}

type Val = { value?: string; from?: string; to?: string };

export function AdvancedSearchDialog({ initialQuery, fields, kinds, lifecycles, onApply, onClose }: Props) {
  const tokens = useMemo(() => fieldTokenMap(fields), [fields]);
  const init = useMemo(() => parseQuery(initialQuery, tokens), [initialQuery, tokens]);
  const clauseFor = (f: FieldDef) =>
    init.clauses.find((c) => c.token === f.key.toLowerCase() || c.token === f.label.toLowerCase());

  const [text, setText] = useState(init.text);
  const [kind, setKind] = useState(init.clauses.find((c) => c.token === "tipo" || c.token === "kind")?.value ?? "");
  const [lifecycle, setLifecycle] = useState(
    init.clauses.find((c) => c.token === "ciclo" || c.token === "lifecycle" || c.token === "estado")?.value ?? "",
  );
  const [vals, setVals] = useState<Record<string, Val>>(() => {
    const o: Record<string, Val> = {};
    for (const f of fields) {
      const c = clauseFor(f);
      if (c) o[f.key] = c.op === "range" ? { from: c.from, to: c.to } : { value: c.value };
    }
    return o;
  });
  const setVal = (key: string, patch: Val) => setVals((s) => ({ ...s, [key]: { ...s[key], ...patch } }));

  const parts = (): QueryPart[] => {
    const p: QueryPart[] = [];
    if (kind) p.push({ token: "tipo", value: kind });
    if (lifecycle) p.push({ token: "ciclo", value: lifecycle });
    for (const f of fields) {
      const v = vals[f.key] ?? {};
      if (isRangeType(f.field_type)) p.push({ token: f.key, from: v.from, to: v.to });
      else p.push({ token: f.key, value: v.value });
    }
    return p;
  };
  const preview = buildQuery(text, parts());

  const clear = () => { setText(""); setKind(""); setLifecycle(""); setVals({}); };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" onClick={onClose}>
      <div className="surface flex max-h-[85vh] w-full max-w-2xl flex-col rounded-lg border shadow-xl"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b px-4 py-3">
          <h2 className="font-semibold">Búsqueda avanzada</h2>
          <button className="btn btn-ghost !p-1" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="grid grid-cols-1 gap-3 overflow-auto p-4 sm:grid-cols-2">
          <label className="sm:col-span-2">
            <span className="text-xs font-medium text-[hsl(var(--muted))]">Texto (nombre o descripción)</span>
            <input className="input w-full" value={text} onChange={(e) => setText(e.target.value)} placeholder="Buscar texto libre…" />
          </label>

          <label>
            <span className="text-xs font-medium text-[hsl(var(--muted))]">Tipo</span>
            <select className="input w-full" value={kind} onChange={(e) => setKind(e.target.value)}>
              <option value="">Cualquiera</option>
              {kinds.map((k) => <option key={k} value={k}>{k}</option>)}
            </select>
          </label>
          <label>
            <span className="text-xs font-medium text-[hsl(var(--muted))]">Ciclo de vida</span>
            <select className="input w-full" value={lifecycle} onChange={(e) => setLifecycle(e.target.value)}>
              <option value="">Cualquiera</option>
              {lifecycles.map((l) => <option key={l} value={l}>{LIFECYCLE_LABEL[l] ?? l}</option>)}
            </select>
          </label>

          {fields.map((f) => (
            <label key={f.key} className={isRangeType(f.field_type) ? "sm:col-span-2" : ""}>
              <span className="text-xs font-medium text-[hsl(var(--muted))]">{f.label}</span>
              {f.field_type === "select" || f.field_type === "multiselect" ? (
                <select className="input w-full" value={vals[f.key]?.value ?? ""} onChange={(e) => setVal(f.key, { value: e.target.value })}>
                  <option value="">Cualquiera</option>
                  {f.options.map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              ) : isRangeType(f.field_type) ? (
                <div className="flex items-center gap-2">
                  <input className="input w-full" type={htmlType(f.field_type)} placeholder="Desde"
                    value={vals[f.key]?.from ?? ""} onChange={(e) => setVal(f.key, { from: e.target.value })} />
                  <span className="text-xs text-[hsl(var(--muted))]">a</span>
                  <input className="input w-full" type={htmlType(f.field_type)} placeholder="Hasta"
                    value={vals[f.key]?.to ?? ""} onChange={(e) => setVal(f.key, { to: e.target.value })} />
                </div>
              ) : (
                <input className="input w-full" value={vals[f.key]?.value ?? ""} onChange={(e) => setVal(f.key, { value: e.target.value })} />
              )}
            </label>
          ))}
        </div>

        <div className="border-t px-4 py-3">
          <div className="mb-2 flex items-center gap-2">
            <span className="text-xs text-[hsl(var(--muted))]">Búsqueda:</span>
            <code className="min-w-0 flex-1 truncate rounded bg-black/5 px-2 py-1 text-xs dark:bg-white/10">{preview || "—"}</code>
          </div>
          <div className="flex items-center justify-end gap-2">
            <button className="btn btn-ghost mr-auto" onClick={clear}>Limpiar</button>
            <button className="btn btn-ghost" onClick={onClose}>Cancelar</button>
            <button className="btn btn-primary" onClick={() => { onApply(preview); onClose(); }}>Aplicar</button>
          </div>
        </div>
      </div>
    </div>
  );
}

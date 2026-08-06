import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { UserPicker } from "../../components/UserPicker";
import { api } from "../../lib/api";
import type { Element, FieldDef } from "../../lib/types";

function FieldInput({ def, value, onChange }: { def: FieldDef; value: unknown; onChange: (v: unknown) => void }) {
  switch (def.field_type) {
    case "longtext":
      return <textarea className="input min-h-16 w-full resize-y" value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)} />;
    case "number":
      return <input type="number" className="input w-full" value={(value as number) ?? ""} onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))} />;
    case "date":
      return <input type="date" className="input w-full" value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)} />;
    case "time":
      return <input type="time" className="input w-full" value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)} />;
    case "select":
      return (
        <select className="input w-full" value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value || null)}>
          <option value="">—</option>
          {def.options.map((o) => <option key={o} value={o}>{o}</option>)}
        </select>
      );
    case "multiselect": {
      const arr = (value as string[]) ?? [];
      return (
        <div className="flex flex-wrap gap-1.5">
          {def.options.map((o) => {
            const on = arr.includes(o);
            return (
              <button key={o} type="button"
                className={`rounded-full border px-2.5 py-0.5 text-xs ${on ? "bg-[hsl(var(--accent))]/15 text-[hsl(var(--accent))]" : ""}`}
                onClick={() => onChange(on ? arr.filter((x) => x !== o) : [...arr, o])}>
                {o}
              </button>
            );
          })}
        </div>
      );
    }
    case "user":
      return <UserPicker value={(value as string) ?? null} onChange={onChange} />;
    case "users":
      return <UserPicker multiple value={(value as string[]) ?? []} onChange={onChange} />;
    default:
      return <input className="input w-full" value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value)} />;
  }
}

export function CustomFields({ element, onSaved }: { element: Element; onSaved: () => void }) {
  const qc = useQueryClient();
  const fields = useQuery({ queryKey: ["fields", element.kind], queryFn: () => api.listFields(element.kind) });
  const [values, setValues] = useState<Record<string, unknown>>(element.custom_fields ?? {});

  useEffect(() => { setValues(element.custom_fields ?? {}); }, [element.slug, element.custom_fields]);

  const save = useMutation({
    mutationFn: () => api.setElementFields(element.slug, values),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["element", element.slug] }); qc.invalidateQueries({ queryKey: ["elements"] }); onSaved(); },
  });

  const defs = fields.data ?? [];
  if (defs.length === 0) return null;

  const dirty = JSON.stringify(values) !== JSON.stringify(element.custom_fields ?? {});

  return (
    <section className="surface rounded-lg border p-4">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[hsl(var(--muted))]">Campos</h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {defs.map((def) => (
          <div key={def.id} className={def.field_type === "longtext" || def.field_type === "multiselect" ? "sm:col-span-2" : ""}>
            <label className="text-xs font-medium text-[hsl(var(--muted))]">{def.label}</label>
            <FieldInput def={def} value={values[def.key]} onChange={(v) => setValues((s) => ({ ...s, [def.key]: v }))} />
          </div>
        ))}
      </div>
      <div className="mt-3 flex justify-end">
        <button className="btn btn-primary disabled:opacity-40" disabled={!dirty || save.isPending} onClick={() => save.mutate()}>
          {save.isPending ? "Guardando…" : "Guardar campos"}
        </button>
      </div>
    </section>
  );
}

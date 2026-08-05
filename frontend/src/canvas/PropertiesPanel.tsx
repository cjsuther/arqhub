import { ExternalLink, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../lib/api";
import type { Element, Lifecycle } from "../lib/types";
import { LifecycleBadge } from "../lib/ui";

const LIFECYCLES: { value: Lifecycle; label: string }[] = [
  { value: "proposed", label: "Propuesto" },
  { value: "active", label: "Activo" },
  { value: "deprecated", label: "Obsoleto" },
  { value: "retired", label: "Retirado" },
];

interface Props {
  element: Element | null;
  onSaved: () => void;
}

export function PropertiesPanel({ element, onSaved }: Props) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  useEffect(() => {
    setName(element?.name ?? "");
    setDescription(element?.description ?? "");
  }, [element]);

  if (!element) {
    return (
      <div className="surface w-72 border-l p-4 text-sm text-[hsl(var(--muted))]">
        Seleccioná un elemento para ver y editar sus propiedades.
      </div>
    );
  }

  const dirty = name !== element.name || description !== (element.description ?? "");

  async function save() {
    await api.updateElement(element!.slug, { name, description: description || null });
    onSaved();
  }

  async function changeLifecycle(lc: Lifecycle) {
    await api.updateElement(element!.slug, { lifecycle: lc });
    onSaved();
  }

  return (
    <div className="surface flex w-72 flex-col gap-3 border-l p-4 text-sm">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">Propiedades</h3>
        <LifecycleBadge value={element.lifecycle} />
      </div>
      <p className="text-xs text-[hsl(var(--muted))]">
        Edita el repositorio — impacta todas las vistas donde aparece.
      </p>

      <label className="text-xs font-medium text-[hsl(var(--muted))]">Nombre</label>
      <input className="input" value={name} onChange={(e) => setName(e.target.value)} />

      <label className="text-xs font-medium text-[hsl(var(--muted))]">Descripción</label>
      <textarea className="input min-h-20 resize-y" value={description}
        onChange={(e) => setDescription(e.target.value)} />

      <label className="text-xs font-medium text-[hsl(var(--muted))]">Ciclo de vida</label>
      <select className="input" value={element.lifecycle}
        onChange={(e) => changeLifecycle(e.target.value as Lifecycle)}>
        {LIFECYCLES.map((lc) => <option key={lc.value} value={lc.value}>{lc.label}</option>)}
      </select>

      <div className="text-xs text-[hsl(var(--muted))]">
        <div>tipo: <code>{element.kind}</code></div>
        {element.domain && <div>dominio: {element.domain}</div>}
        <div>slug: <code>{element.slug}</code></div>
      </div>

      <div className="mt-auto flex items-center gap-2">
        <button className="btn btn-primary flex-1 justify-center disabled:opacity-40"
          disabled={!dirty} onClick={save}>
          <Save size={15} /> Guardar
        </button>
        <Link className="btn btn-ghost" to={`/catalog/${element.slug}`} title="Ver ficha">
          <ExternalLink size={15} />
        </Link>
      </div>
    </div>
  );
}

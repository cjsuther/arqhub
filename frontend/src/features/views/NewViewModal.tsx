import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { api } from "../../lib/api";
import { langLabel } from "../../lib/ui";

function slugify(text: string): string {
  return text.trim().toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

export function NewViewModal({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const registry = useQuery({ queryKey: ["registry"], queryFn: api.registry });
  const [name, setName] = useState("");
  const [lang, setLang] = useState("archimate");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const slug = slugify(name);

  async function create() {
    if (!slug) return setError("Poné un nombre.");
    setBusy(true);
    setError(null);
    try {
      await api.createView({ slug, name, lang });
      navigate(`/views/${slug}/edit`);
    } catch (e) {
      setError(e instanceof Error ? e.message.replace(/^\d+ [^:]+: /, "").slice(0, 140) : "Error");
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="surface w-96 rounded-lg border p-4 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Nueva vista</h3>
          <button className="btn btn-ghost !border-transparent !p-1" onClick={onClose}><X size={16} /></button>
        </div>

        <label className="mt-3 block text-xs font-medium text-[hsl(var(--muted))]">Nombre</label>
        <input className="input mt-1 w-full" autoFocus value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && create()}
          placeholder="Ej: Cooperación de Aplicaciones" />
        {slug && <p className="mt-1 text-xs text-[hsl(var(--muted))]">slug: <code>{slug}</code></p>}

        <label className="mt-3 block text-xs font-medium text-[hsl(var(--muted))]">Lenguaje</label>
        <select className="input mt-1 w-full" value={lang} onChange={(e) => setLang(e.target.value)}>
          {(registry.data?.langs ?? ["archimate", "bpmn", "uml"]).map((l) => (
            <option key={l} value={l}>{langLabel(l)}</option>
          ))}
        </select>

        {error && <p className="mt-3 text-xs text-red-500">{error}</p>}

        <div className="mt-4 flex justify-end gap-2">
          <button className="btn btn-ghost" onClick={onClose}>Cancelar</button>
          <button className="btn btn-primary disabled:opacity-40" disabled={busy || !slug} onClick={create}>
            Crear y editar
          </button>
        </div>
      </div>
    </div>
  );
}

import { useQuery } from "@tanstack/react-query";
import { LayoutGrid, Plus } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../lib/api";
import { StatusBadge, langLabel } from "../../lib/ui";
import { NewViewModal } from "./NewViewModal";

export function ViewsPage() {
  const views = useQuery({ queryKey: ["views"], queryFn: api.listViews });
  const [creating, setCreating] = useState(false);

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Vistas</h1>
          <p className="text-sm text-[hsl(var(--muted))]">
            Las vistas son proyecciones del modelo. Creá una y armala en el editor canvas.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setCreating(true)}>
          <Plus size={16} /> Nueva vista
        </button>
      </div>
      {creating && <NewViewModal onClose={() => setCreating(false)} />}

      {views.isError && (
        <p className="text-sm text-red-500">Error al cargar. ¿Está el backend en :8000?</p>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {views.data?.map((v) => (
          <Link key={v.slug} to={`/views/${v.slug}/edit`}
            className="surface rounded-lg border p-4 transition hover:shadow-sm hover:-translate-y-0.5">
            <div className="mb-3 flex aspect-video items-center justify-center overflow-hidden rounded-md bg-black/5 dark:bg-white/5">
              <img src={`/api/v1/views/${v.slug}/render`} alt={v.name}
                className="h-full w-full object-contain"
                onError={(e) => { e.currentTarget.style.display = "none"; }} />
              <LayoutGrid className="text-[hsl(var(--muted))]" />
            </div>
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-medium leading-tight">{v.name}</h3>
              <StatusBadge value={v.status} />
            </div>
            <div className="mt-2 flex items-center gap-2 text-xs text-[hsl(var(--muted))]">
              <span className="badge bg-black/5 dark:bg-white/10">{langLabel(v.lang)}</span>
              <span>v{v.current_version}</span>
              <span>· {v.include.elements.length} elementos</span>
            </div>
          </Link>
        ))}
      </div>

      {views.data?.length === 0 && (
        <p className="text-sm text-[hsl(var(--muted))]">Todavía no hay vistas.</p>
      )}
    </div>
  );
}

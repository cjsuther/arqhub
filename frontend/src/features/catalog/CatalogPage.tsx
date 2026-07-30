import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../../lib/api";
import { KindBadge, LifecycleBadge } from "../../lib/ui";

export function CatalogPage() {
  const [q, setQ] = useState("");
  const [kind, setKind] = useState("");
  const [lifecycle, setLifecycle] = useState("");

  const registry = useQuery({ queryKey: ["registry"], queryFn: api.registry });
  const elements = useQuery({
    queryKey: ["elements", { q, kind, lifecycle }],
    queryFn: () =>
      api.listElements({ q: q || undefined, kind: kind || undefined, lifecycle: lifecycle || undefined }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Catálogo</h1>
          <p className="text-sm text-[hsl(var(--muted))]">
            El catálogo de elementos <em>es</em> el modelo. Un elemento se define una sola vez.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <input className="input flex-1 min-w-48" placeholder="Buscar por nombre o descripción…"
          value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="input" value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="">Todos los tipos</option>
          {registry.data && Object.keys(registry.data.kinds).map((k) => (
            <option key={k} value={k}>{k}</option>
          ))}
        </select>
        <select className="input" value={lifecycle} onChange={(e) => setLifecycle(e.target.value)}>
          <option value="">Todo el ciclo de vida</option>
          {registry.data?.lifecycles.map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
      </div>

      {elements.isLoading && <p className="text-sm text-[hsl(var(--muted))]">Cargando…</p>}
      {elements.isError && (
        <p className="text-sm text-red-500">Error al cargar. ¿Está el backend en :8000?</p>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {elements.data?.map((el) => (
          <Link key={el.slug} to={`/catalog/${el.slug}`}
            className="surface rounded-lg border p-4 transition hover:shadow-sm hover:-translate-y-0.5">
            <div className="flex items-start justify-between gap-2">
              <h3 className="font-medium leading-tight">{el.name}</h3>
              <LifecycleBadge value={el.lifecycle} />
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <KindBadge registry={registry.data} kind={el.kind} />
              {el.domain && <span className="text-xs text-[hsl(var(--muted))]">{el.domain}</span>}
            </div>
            {el.description && (
              <p className="mt-2 line-clamp-2 text-sm text-[hsl(var(--muted))]">{el.description}</p>
            )}
          </Link>
        ))}
      </div>

      {elements.data?.length === 0 && (
        <p className="text-sm text-[hsl(var(--muted))]">
          No hay elementos. Importá un DSL con <code>POST /api/v1/dsl/import</code>.
        </p>
      )}
    </div>
  );
}

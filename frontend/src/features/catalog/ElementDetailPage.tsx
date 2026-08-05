import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ArrowRight, ArrowLeftRight } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { FolderSelect } from "../../components/FolderSelect";
import { api } from "../../lib/api";
import { KindBadge, LifecycleBadge, StatusBadge, langLabel } from "../../lib/ui";

export function ElementDetailPage() {
  const { slug = "" } = useParams();
  const qc = useQueryClient();
  const registry = useQuery({ queryKey: ["registry"], queryFn: api.registry });
  const element = useQuery({ queryKey: ["element", slug], queryFn: () => api.getElement(slug) });
  const moveFolder = useMutation({
    mutationFn: (folderId: string | null) => api.setElementFolder(slug, folderId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["element", slug] });
      qc.invalidateQueries({ queryKey: ["elements"] });
    },
  });
  const relationships = useQuery({ queryKey: ["relationships"], queryFn: api.listRelationships });
  const views = useQuery({ queryKey: ["views"], queryFn: api.listViews });

  if (element.isError)
    return <p className="text-sm text-red-500">No se encontró el elemento «{slug}».</p>;
  const el = element.data;

  // Navigation: where this element appears (SPEC §1, §8.1) — computed from views.
  const inViews = (views.data ?? []).filter((v) => v.include.elements.includes(slug));
  const rels = (relationships.data ?? []).filter((r) => r.from === slug || r.to === slug);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link to="/catalog" className="btn btn-ghost w-max"><ArrowLeft size={16} /> Catálogo</Link>

      {el && (
        <>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold">{el.name}</h1>
              <LifecycleBadge value={el.lifecycle} />
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-[hsl(var(--muted))]">
              <KindBadge registry={registry.data} kind={el.kind} />
              <code className="text-xs">{el.slug}</code>
              {el.domain && <span>· dominio: {el.domain}</span>}
              {el.owner && <span>· owner: {el.owner}</span>}
            </div>
            {el.description && <p className="mt-3">{el.description}</p>}
            {el.tags.length > 0 && (
              <div className="mt-3 flex flex-wrap gap-1.5">
                {el.tags.map((t) => (
                  <span key={t} className="badge bg-black/5 dark:bg-white/10">#{t}</span>
                ))}
              </div>
            )}
            <div className="mt-3 flex items-center gap-2 text-sm">
              <span className="text-[hsl(var(--muted))]">Carpeta:</span>
              <FolderSelect scope="element" value={el.folder_id}
                onChange={(id) => moveFolder.mutate(id)} className="input !py-1 text-sm" />
            </div>
          </div>

          <section className="surface rounded-lg border p-4">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[hsl(var(--muted))]">
              Relaciones ({rels.length})
            </h2>
            {rels.length === 0 && <p className="text-sm text-[hsl(var(--muted))]">Sin relaciones.</p>}
            <ul className="space-y-1.5">
              {rels.map((r) => {
                const outgoing = r.from === slug;
                const other = outgoing ? r.to : r.from;
                return (
                  <li key={r.slug} className="flex items-center gap-2 text-sm">
                    {outgoing ? <ArrowRight size={15} /> : <ArrowLeftRight size={15} />}
                    <span className="badge bg-black/5 dark:bg-white/10">{r.kind}</span>
                    <Link to={`/catalog/${other}`} className="text-[hsl(var(--accent))] hover:underline">
                      {other}
                    </Link>
                    {r.label && <span className="text-[hsl(var(--muted))]">— {r.label}</span>}
                  </li>
                );
              })}
            </ul>
          </section>

          <section className="surface rounded-lg border p-4">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-[hsl(var(--muted))]">
              Aparece en ({inViews.length})
            </h2>
            {inViews.length === 0 && (
              <p className="text-sm text-[hsl(var(--muted))]">No aparece en ninguna vista.</p>
            )}
            <ul className="space-y-1.5">
              {inViews.map((v) => (
                <li key={v.slug} className="flex items-center gap-2 text-sm">
                  <span className="badge bg-black/5 dark:bg-white/10">{langLabel(v.lang)}</span>
                  <Link to={`/views/${v.slug}/edit`} className="text-[hsl(var(--accent))] hover:underline">
                    {v.name}
                  </Link>
                  <StatusBadge value={v.status} />
                </li>
              ))}
            </ul>
          </section>
        </>
      )}
    </div>
  );
}

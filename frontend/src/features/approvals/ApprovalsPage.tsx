import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Rocket, X } from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "../../lib/api";
import { StatusBadge } from "../../lib/ui";

const STATUS_LABEL: Record<string, string> = {
  pending: "Pendiente",
  approved: "Aprobada",
  rejected: "Rechazada",
  cancelled: "Cancelada",
};

export function ApprovalsPage() {
  const qc = useQueryClient();
  const approvals = useQuery({ queryKey: ["approvals"], queryFn: () => api.listApprovals() });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["approvals"] });
    qc.invalidateQueries({ queryKey: ["views"] });
  };

  const resolve = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "approve" | "reject" }) =>
      action === "approve" ? api.approve(id) : api.reject(id),
    onSuccess: invalidate,
  });

  const publish = useMutation({
    mutationFn: (slug: string) => api.publishView(slug),
    onSuccess: invalidate,
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Aprobaciones</h1>
        <p className="text-sm text-[hsl(var(--muted))]">
          Aprobar habilita la publicación; la vista recién pasa a <strong>Publicada</strong> con el botón Publicar.
        </p>
      </div>

      {approvals.isError && <p className="text-sm text-red-500">Error al cargar.</p>}

      <div className="surface overflow-hidden rounded-lg border">
        <table className="w-full text-sm">
          <thead className="border-b text-left text-xs uppercase text-[hsl(var(--muted))]">
            <tr>
              <th className="px-4 py-2 font-medium">Vista</th>
              <th className="px-4 py-2 font-medium">Versión</th>
              <th className="px-4 py-2 font-medium">Solicitud</th>
              <th className="px-4 py-2 font-medium">Estado vista</th>
              <th className="px-4 py-2 font-medium">Solicitante</th>
              <th className="px-4 py-2" />
            </tr>
          </thead>
          <tbody>
            {approvals.data?.map((a) => (
              <tr key={a.id} className="border-b last:border-0">
                <td className="px-4 py-2">
                  <Link to={`/views/${a.view_slug}/edit`} className="text-[hsl(var(--accent))] hover:underline">
                    {a.view_slug}
                  </Link>
                </td>
                <td className="px-4 py-2">v{a.view_version}</td>
                <td className="px-4 py-2">{STATUS_LABEL[a.status] ?? a.status}</td>
                <td className="px-4 py-2"><StatusBadge value={a.view_status} /></td>
                <td className="px-4 py-2 text-[hsl(var(--muted))]">{a.requested_by_name ?? "—"}</td>
                <td className="px-4 py-2 text-right">
                  {a.status === "pending" && (
                    <div className="flex justify-end gap-1.5">
                      <button className="btn btn-ghost !py-1" disabled={resolve.isPending}
                        onClick={() => resolve.mutate({ id: a.id, action: "approve" })}>
                        <Check size={14} /> Aprobar
                      </button>
                      <button className="btn btn-ghost !py-1" disabled={resolve.isPending}
                        onClick={() => resolve.mutate({ id: a.id, action: "reject" })}>
                        <X size={14} /> Rechazar
                      </button>
                    </div>
                  )}
                  {a.status === "approved" && a.view_status !== "published" && (
                    <button className="btn btn-primary !py-1" disabled={publish.isPending}
                      onClick={() => publish.mutate(a.view_slug)}>
                      <Rocket size={14} /> Publicar
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {approvals.data?.length === 0 && (
          <p className="px-4 py-6 text-center text-sm text-[hsl(var(--muted))]">No hay solicitudes.</p>
        )}
      </div>
    </div>
  );
}

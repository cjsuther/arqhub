import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, X } from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "../../lib/api";

const STATUS_LABEL: Record<string, string> = {
  pending: "Pendiente",
  approved: "Aprobada",
  rejected: "Rechazada",
  cancelled: "Cancelada",
};

export function ApprovalsPage() {
  const qc = useQueryClient();
  const approvals = useQuery({ queryKey: ["approvals"], queryFn: () => api.listApprovals() });

  const resolve = useMutation({
    mutationFn: ({ id, action }: { id: string; action: "approve" | "reject" }) =>
      action === "approve" ? api.approve(id) : api.reject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["approvals"] }),
  });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Aprobaciones</h1>
        <p className="text-sm text-[hsl(var(--muted))]">Solicitudes de revisión de vistas.</p>
      </div>

      {approvals.isError && <p className="text-sm text-red-500">Error al cargar.</p>}

      <div className="surface overflow-hidden rounded-lg border">
        <table className="w-full text-sm">
          <thead className="border-b text-left text-xs uppercase text-[hsl(var(--muted))]">
            <tr>
              <th className="px-4 py-2 font-medium">Vista</th>
              <th className="px-4 py-2 font-medium">Versión</th>
              <th className="px-4 py-2 font-medium">Estado</th>
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
                <td className="px-4 py-2 text-[hsl(var(--muted))]">{a.requested_by ?? "—"}</td>
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

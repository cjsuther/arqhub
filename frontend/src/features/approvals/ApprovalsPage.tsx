import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Rocket, X } from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "../../lib/api";
import type { Approval } from "../../lib/types";
import { StatusBadge, formatDate } from "../../lib/ui";

const STATUS_LABEL: Record<string, string> = {
  pending: "Pendiente",
  approved: "Aprobada",
  rejected: "Rechazada",
  cancelled: "Cancelada",
};
const STATUS_CLASS: Record<string, string> = {
  pending: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  approved: "bg-green-500/15 text-green-700 dark:text-green-300",
  rejected: "bg-red-500/15 text-red-700 dark:text-red-300",
  cancelled: "bg-gray-500/15 text-gray-500",
};

export function ApprovalsPage() {
  const qc = useQueryClient();
  const approvals = useQuery({ queryKey: ["approvals"], queryFn: () => api.listApprovals() });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["approvals"] });
    qc.invalidateQueries({ queryKey: ["views"] });
  };
  const resolve = useMutation({
    mutationFn: ({ id, action, comment }: { id: string; action: "approve" | "reject"; comment: string }) =>
      action === "approve" ? api.approve(id, comment) : api.reject(id, comment),
    onSuccess: invalidate,
  });
  const publish = useMutation({ mutationFn: (slug: string) => api.publishView(slug), onSuccess: invalidate });

  function decide(id: string, action: "approve" | "reject") {
    const verb = action === "approve" ? "aprobar" : "rechazar";
    const comment = window.prompt(`Comentario para ${verb} (obligatorio):`);
    if (comment === null) return;
    if (!comment.trim()) { window.alert("El comentario es obligatorio."); return; }
    resolve.mutate({ id, action, comment: comment.trim() });
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Aprobaciones</h1>
        <p className="text-sm text-[hsl(var(--muted))]">
          Aprobar/rechazar requiere un comentario. La vista se publica con el botón Publicar tras la aprobación.
        </p>
      </div>

      {approvals.isError && <p className="text-sm text-red-500">Error al cargar.</p>}
      {approvals.data?.length === 0 && (
        <p className="text-sm text-[hsl(var(--muted))]">No hay solicitudes.</p>
      )}

      <div className="space-y-3">
        {approvals.data?.map((a) => <ApprovalCard key={a.id} a={a} onDecide={decide} onPublish={(s) => publish.mutate(s)}
          busy={resolve.isPending || publish.isPending} />)}
      </div>
    </div>
  );
}

function ApprovalCard({ a, onDecide, onPublish, busy }: {
  a: Approval;
  onDecide: (id: string, action: "approve" | "reject") => void;
  onPublish: (slug: string) => void;
  busy: boolean;
}) {
  const decidedBy = new Set(a.decisions.map((d) => d.approver_id));
  const pendingApprovers = a.approvers
    .map((id, i) => ({ id, name: a.approver_names[i] ?? id }))
    .filter((x) => !decidedBy.has(x.id));

  return (
    <div className="surface rounded-lg border p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Link to={`/views/${a.view_slug}/edit`} className="font-medium text-[hsl(var(--accent))] hover:underline">
          {a.view_slug}
        </Link>
        <span className="text-xs text-[hsl(var(--muted))]">v{a.view_version}</span>
        <span className={`badge ${STATUS_CLASS[a.status]}`}>{STATUS_LABEL[a.status] ?? a.status}</span>
        <span className="text-xs text-[hsl(var(--muted))]">vista:</span>
        <StatusBadge value={a.view_status} />
        <div className="ml-auto flex items-center gap-1.5">
          {a.status === "pending" && (
            <>
              <button className="btn btn-ghost !py-1" disabled={busy} onClick={() => onDecide(a.id, "approve")}>
                <Check size={14} /> Aprobar
              </button>
              <button className="btn btn-ghost !py-1" disabled={busy} onClick={() => onDecide(a.id, "reject")}>
                <X size={14} /> Rechazar
              </button>
            </>
          )}
          {a.status === "approved" && a.view_status !== "published" && (
            <button className="btn btn-primary !py-1" disabled={busy} onClick={() => onPublish(a.view_slug)}>
              <Rocket size={14} /> Publicar
            </button>
          )}
        </div>
      </div>

      <p className="mt-2 text-xs text-[hsl(var(--muted))]">
        Solicitada por <strong>{a.requested_by_name ?? "—"}</strong>
        {a.created_at && <> · {formatDate(a.created_at)}</>}
      </p>

      {/* Per-approver decisions (who + when + comment). */}
      {(a.decisions.length > 0 || pendingApprovers.length > 0) && (
        <div className="mt-3 space-y-1.5 border-t pt-3">
          {a.decisions.map((d, i) => (
            <div key={i} className="text-sm">
              <span className={d.decision === "approved" ? "text-green-600" : "text-red-600"}>
                {d.decision === "approved" ? "✓ Aprobó" : "✗ Rechazó"}
              </span>{" "}
              <strong>{d.approver_name ?? "—"}</strong>
              <span className="text-xs text-[hsl(var(--muted))]"> · {formatDate(d.decided_at)}</span>
              {d.comment && <div className="pl-4 text-[hsl(var(--muted))]">“{d.comment}”</div>}
            </div>
          ))}
          {pendingApprovers.map((x) => (
            <div key={x.id} className="text-sm text-[hsl(var(--muted))]">
              <span className="text-amber-600">◷ Pendiente</span> <strong>{x.name}</strong>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

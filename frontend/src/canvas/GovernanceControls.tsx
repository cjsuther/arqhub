import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Check, Rocket, Send, X } from "lucide-react";
import { useState } from "react";

import { api } from "../lib/api";
import type { View } from "../lib/types";
import { SubmitReviewModal } from "./SubmitReviewModal";

export function GovernanceControls({ view, onChanged }: { view: View; onChanged: () => void }) {
  const qc = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [reviewing, setReviewing] = useState(false);

  const me = useQuery({ queryKey: ["me"], queryFn: api.getMe });
  const approvals = useQuery({ queryKey: ["approvals"], queryFn: () => api.listApprovals() });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["approvals"] });
    onChanged();
  };
  const onErr = (e: unknown) =>
    setError(e instanceof Error ? e.message.replace(/^\d+ [^:]+: /, "").slice(0, 140) : "Error");

  const submit = useMutation({
    mutationFn: (v: { approvers: string[]; comment: string }) =>
      api.submitReview(view.slug, v.approvers, v.comment || undefined),
    onSuccess: () => { setReviewing(false); refresh(); },
    onError: onErr,
  });
  const decide = useMutation({
    mutationFn: (v: { id: string; action: "approve" | "reject"; comment: string }) =>
      v.action === "approve" ? api.approve(v.id, v.comment) : api.reject(v.id, v.comment),
    onSuccess: refresh,
    onError: onErr,
  });
  const publish = useMutation({ mutationFn: () => api.publishView(view.slug), onSuccess: refresh, onError: onErr });
  const deprecate = useMutation({ mutationFn: () => api.deprecateView(view.slug), onSuccess: refresh, onError: onErr });

  const list = approvals.data ?? [];
  const pending = list.find((a) => a.view_slug === view.slug && a.status === "pending");
  const approved = list.find(
    (a) => a.view_slug === view.slug && a.status === "approved" && a.view_version === view.current_version,
  );
  const canApprove = me.data?.role === "approver" || me.data?.role === "admin";
  const busy = submit.isPending || decide.isPending || publish.isPending || deprecate.isPending;

  function decideWithComment(action: "approve" | "reject") {
    if (!pending) return;
    const verb = action === "approve" ? "aprobar" : "rechazar";
    const comment = window.prompt(`Comentario para ${verb} (obligatorio):`);
    if (comment === null) return;
    if (!comment.trim()) { window.alert("El comentario es obligatorio."); return; }
    decide.mutate({ id: pending.id, action, comment: comment.trim() });
  }

  return (
    <div className="flex items-center gap-2">
      {error && <span className="text-xs text-red-500">{error}</span>}

      {view.status === "draft" && (
        <button className="btn btn-ghost" disabled={busy} onClick={() => setReviewing(true)}>
          <Send size={15} /> Enviar a revisión
        </button>
      )}
      {reviewing && (
        <SubmitReviewModal onSubmit={(a, c) => submit.mutate({ approvers: a, comment: c })}
          onCancel={() => setReviewing(false)} busy={submit.isPending} />
      )}

      {view.status === "in_review" && pending && canApprove && (
        <>
          <button className="btn btn-ghost" disabled={busy} onClick={() => decideWithComment("approve")}>
            <Check size={15} /> Aprobar
          </button>
          <button className="btn btn-ghost" disabled={busy} onClick={() => decideWithComment("reject")}>
            <X size={15} /> Rechazar
          </button>
        </>
      )}
      {view.status === "in_review" && pending && !canApprove && (
        <span className="text-xs text-[hsl(var(--muted))]">En revisión — requiere un aprobador</span>
      )}
      {view.status === "in_review" && approved && (
        <button className="btn btn-primary" disabled={busy} onClick={() => publish.mutate()}>
          <Rocket size={15} /> Publicar
        </button>
      )}

      {view.status === "published" && (
        <button className="btn btn-ghost" disabled={busy} onClick={() => deprecate.mutate()}>
          <Archive size={15} /> Deprecar
        </button>
      )}
    </div>
  );
}

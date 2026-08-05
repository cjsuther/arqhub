import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Send, Trash2, X } from "lucide-react";
import { useState } from "react";

import { api } from "../lib/api";

interface Props {
  slug: string;
  onClose: () => void;
}

function when(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? "" : d.toLocaleString();
}

export function CommentsPanel({ slug, onClose }: Props) {
  const qc = useQueryClient();
  const comments = useQuery({ queryKey: ["comments", slug], queryFn: () => api.listComments(slug) });
  const [body, setBody] = useState("");

  const invalidate = () => qc.invalidateQueries({ queryKey: ["comments", slug] });
  const add = useMutation({
    mutationFn: () => api.addComment(slug, body.trim()),
    onSuccess: () => { setBody(""); invalidate(); },
  });
  const del = useMutation({ mutationFn: (id: string) => api.deleteComment(id), onSuccess: invalidate });

  return (
    <aside className="surface flex w-80 flex-col border-l">
      <div className="flex items-center justify-between border-b px-4 py-2.5">
        <h3 className="font-semibold">Comentarios</h3>
        <button className="btn btn-ghost !p-1" onClick={onClose}><X size={16} /></button>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-auto p-3">
        {comments.data?.length === 0 && (
          <p className="text-sm text-[hsl(var(--muted))]">Sin comentarios todavía.</p>
        )}
        {comments.data?.map((c) => (
          <div key={c.id} className="group rounded-lg border p-2.5 text-sm">
            <div className="mb-1 flex items-center justify-between gap-2">
              <span className="font-medium">{c.author_name ?? "—"}</span>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-[hsl(var(--muted))]">{when(c.created_at)}</span>
                <button className="text-[hsl(var(--muted))] opacity-0 hover:text-red-500 group-hover:opacity-100"
                  title="Borrar" onClick={() => del.mutate(c.id)}><Trash2 size={13} /></button>
              </div>
            </div>
            <p className="whitespace-pre-wrap break-words text-[hsl(var(--fg))]">{c.body}</p>
          </div>
        ))}
      </div>

      <div className="border-t p-3">
        <textarea className="input min-h-16 w-full resize-y text-sm" placeholder="Escribí un comentario…"
          value={body} onChange={(e) => setBody(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && body.trim()) add.mutate(); }} />
        <button className="btn btn-primary mt-2 w-full justify-center" disabled={!body.trim() || add.isPending}
          onClick={() => add.mutate()}>
          <Send size={14} /> Comentar
        </button>
      </div>
    </aside>
  );
}

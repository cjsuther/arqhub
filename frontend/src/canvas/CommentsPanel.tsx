import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AtSign, Send, Trash2, X } from "lucide-react";
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
  const users = useQuery({ queryKey: ["users"], queryFn: () => api.listUsers() });
  const [body, setBody] = useState("");
  const [mentions, setMentions] = useState<string[]>([]);
  const [pickMentions, setPickMentions] = useState(false);

  const invalidate = () => qc.invalidateQueries({ queryKey: ["comments", slug] });
  const add = useMutation({
    mutationFn: () => api.addComment(slug, body.trim(), mentions),
    onSuccess: () => { setBody(""); setMentions([]); invalidate(); },
  });
  const del = useMutation({ mutationFn: (id: string) => api.deleteComment(id), onSuccess: invalidate });

  const nameOf = (id: string) => users.data?.find((u) => u.id === id)?.display_name ?? id;
  const toggleMention = (id: string) =>
    setMentions((m) => (m.includes(id) ? m.filter((x) => x !== id) : [...m, id]));

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

      <div className="relative border-t p-3">
        {mentions.length > 0 && (
          <div className="mb-1.5 flex flex-wrap gap-1">
            {mentions.map((id) => (
              <span key={id} className="flex items-center gap-1 rounded-full bg-[hsl(var(--accent))]/15 px-2 py-0.5 text-xs text-[hsl(var(--accent))]">
                @{nameOf(id)}
                <button onClick={() => toggleMention(id)}><X size={11} /></button>
              </span>
            ))}
          </div>
        )}
        <textarea className="input min-h-16 w-full resize-y text-sm" placeholder="Escribí un comentario…"
          value={body} onChange={(e) => setBody(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && body.trim()) add.mutate(); }} />
        <div className="mt-2 flex items-center gap-2">
          <button className="btn btn-ghost !py-1" title="Mencionar a alguien" onClick={() => setPickMentions((p) => !p)}>
            <AtSign size={14} /> Mencionar
          </button>
          <button className="btn btn-primary flex-1 justify-center" disabled={!body.trim() || add.isPending}
            onClick={() => add.mutate()}>
            <Send size={14} /> Comentar
          </button>
        </div>
        {pickMentions && (
          <div className="absolute bottom-14 left-3 z-20 max-h-48 w-56 overflow-auto rounded-lg border bg-[hsl(var(--bg))] p-1 shadow-lg">
            {users.data?.map((u) => (
              <label key={u.id} className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-sm hover:bg-black/5 dark:hover:bg-white/5">
                <input type="checkbox" checked={mentions.includes(u.id)} onChange={() => toggleMention(u.id)} />
                <span className="flex-1 truncate">{u.display_name}</span>
              </label>
            ))}
            <button className="btn btn-ghost !py-1 mt-1 w-full justify-center" onClick={() => setPickMentions(false)}>Listo</button>
          </div>
        )}
      </div>
    </aside>
  );
}

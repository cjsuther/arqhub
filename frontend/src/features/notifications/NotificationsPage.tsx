import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AtSign, Bell, CheckCheck, CheckCircle2, Share2, Send } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { api } from "../../lib/api";
import type { AppNotification } from "../../lib/types";
import { formatDate } from "../../lib/ui";

const ICON: Record<string, typeof Bell> = {
  approval_requested: Send,
  approval_resolved: CheckCircle2,
  comment_mention: AtSign,
  draft_shared: Share2,
};

export function NotificationsPage() {
  const qc = useQueryClient();
  const navigate = useNavigate();
  const notifications = useQuery({ queryKey: ["notifications"], queryFn: () => api.listNotifications() });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["notifications"] });
    qc.invalidateQueries({ queryKey: ["notifications", "count"] });
  };
  const readOne = useMutation({ mutationFn: (id: string) => api.markNotificationRead(id), onSuccess: invalidate });
  const readAll = useMutation({ mutationFn: () => api.markAllNotificationsRead(), onSuccess: invalidate });

  function open(n: AppNotification) {
    if (!n.read) readOne.mutate(n.id);
    if (n.view_slug) navigate(`/views/${n.view_slug}/edit`);
  }

  const list = notifications.data ?? [];
  const unread = list.filter((n) => !n.read).length;

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Notificaciones</h1>
          <p className="text-sm text-[hsl(var(--muted))]">
            {unread > 0 ? `${unread} sin leer` : "Todo al día"}.
          </p>
        </div>
        {unread > 0 && (
          <button className="btn btn-ghost" onClick={() => readAll.mutate()} disabled={readAll.isPending}>
            <CheckCheck size={15} /> Marcar todo como leído
          </button>
        )}
      </div>

      {notifications.isError && <p className="text-sm text-red-500">Error al cargar.</p>}
      {list.length === 0 && (
        <div className="rounded-lg border p-8 text-center text-sm text-[hsl(var(--muted))]">
          <Bell className="mx-auto mb-2 opacity-50" />
          No tenés notificaciones.
        </div>
      )}

      <div className="space-y-1.5">
        {list.map((n) => {
          const Icon = ICON[n.kind] ?? Bell;
          return (
            <button key={n.id} onClick={() => open(n)}
              className={`surface flex w-full items-start gap-3 rounded-lg border p-3 text-left transition hover:shadow-sm ${
                n.read ? "opacity-70" : "border-[hsl(var(--accent))]/40"
              }`}>
              <span className={`mt-0.5 shrink-0 ${n.read ? "text-[hsl(var(--muted))]" : "text-[hsl(var(--accent))]"}`}>
                <Icon size={18} />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className={`truncate ${n.read ? "" : "font-medium"}`}>{n.title}</span>
                  {!n.read && <span className="h-2 w-2 shrink-0 rounded-full bg-[hsl(var(--accent))]" />}
                </div>
                {n.body && <p className="mt-0.5 line-clamp-2 text-sm text-[hsl(var(--muted))]">{n.body}</p>}
                <p className="mt-0.5 text-[11px] text-[hsl(var(--muted))]">{formatDate(n.created_at)}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

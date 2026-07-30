import { CheckCircle2, Send, Archive } from "lucide-react";
import { useState } from "react";

import { api } from "../lib/api";
import type { View } from "../lib/types";

export function GovernanceControls({ view, onChanged }: { view: View; onChanged: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message.replace(/^\d+ [^:]+: /, "").slice(0, 120) : "Error");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex items-center gap-2">
      {error && <span className="text-xs text-red-500">{error}</span>}
      {view.status === "draft" && (
        <button className="btn btn-ghost" disabled={busy}
          onClick={() => run(() => api.submitReview(view.slug, []))}>
          <Send size={15} /> Enviar a revisión
        </button>
      )}
      {view.status === "in_review" && (
        <button className="btn btn-ghost" disabled={busy}
          onClick={() => run(() => api.publishView(view.slug))}>
          <CheckCircle2 size={15} /> Publicar
        </button>
      )}
      {view.status === "published" && (
        <button className="btn btn-ghost" disabled={busy}
          onClick={() => run(() => api.deprecateView(view.slug))}>
          <Archive size={15} /> Deprecar
        </button>
      )}
    </div>
  );
}

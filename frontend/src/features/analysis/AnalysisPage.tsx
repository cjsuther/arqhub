import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Info, XCircle } from "lucide-react";
import { Link } from "react-router-dom";

import { api } from "../../lib/api";
import type { Finding } from "../../lib/types";

const SEVERITY: Record<Finding["severity"], { icon: typeof Info; cls: string }> = {
  error: { icon: XCircle, cls: "text-red-500" },
  warning: { icon: AlertTriangle, cls: "text-amber-500" },
  info: { icon: Info, cls: "text-blue-500" },
};

export function AnalysisPage() {
  const analysis = useQuery({ queryKey: ["analysis"], queryFn: api.analyze });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Análisis del modelo</h1>
        <p className="text-sm text-[hsl(var(--muted))]">
          Reglas determinísticas: duplicados, huérfanos, ciclo de vida, acoplamiento y matriz.
        </p>
      </div>

      {analysis.isLoading && <p className="text-sm text-[hsl(var(--muted))]">Analizando…</p>}
      {analysis.isError && <p className="text-sm text-red-500">Error al analizar.</p>}
      {analysis.data?.length === 0 && (
        <p className="text-sm text-green-600 dark:text-green-400">Sin hallazgos. El modelo está limpio. ✨</p>
      )}

      <div className="space-y-2">
        {analysis.data?.map((f, i) => {
          const S = SEVERITY[f.severity];
          return (
            <div key={i} className="surface flex items-start gap-3 rounded-lg border p-3">
              <S.icon size={18} className={`mt-0.5 shrink-0 ${S.cls}`} />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="badge bg-black/5 dark:bg-white/10">{f.code}</span>
                </div>
                <p className="mt-1 text-sm">{f.message}</p>
                {f.suggestion && (
                  <p className="mt-1 text-xs text-[hsl(var(--muted))]">→ {f.suggestion}</p>
                )}
                {f.entities.length > 0 && (
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {f.entities.map((e) => (
                      <Link key={e} to={`/catalog/${e}`} className="text-xs text-[hsl(var(--accent))] hover:underline">
                        {e}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

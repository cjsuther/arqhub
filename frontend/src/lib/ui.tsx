import type { Lifecycle, Registry, ViewStatus } from "./types";

const LAYER_BG: Record<string, string> = {
  business: "bg-layer-business/20 text-yellow-800 dark:text-yellow-300",
  application: "bg-layer-application/20 text-blue-800 dark:text-blue-300",
  technology: "bg-layer-technology/20 text-green-800 dark:text-green-300",
  motivation: "bg-layer-motivation/20 text-purple-800 dark:text-purple-300",
};

export function kindLayer(registry: Registry | undefined, kind: string): string {
  return registry?.kinds[kind]?.layer ?? "application";
}

export function KindBadge({ registry, kind }: { registry?: Registry; kind: string }) {
  const layer = kindLayer(registry, kind);
  return <span className={`badge ${LAYER_BG[layer]}`}>{kind}</span>;
}

const LIFECYCLE_BG: Record<Lifecycle, string> = {
  proposed: "bg-blue-500/15 text-blue-700 dark:text-blue-300",
  active: "bg-green-500/15 text-green-700 dark:text-green-300",
  deprecated: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  retired: "bg-gray-500/15 text-gray-600 dark:text-gray-300",
};

export function LifecycleBadge({ value }: { value: Lifecycle }) {
  return <span className={`badge ${LIFECYCLE_BG[value]}`}>{value}</span>;
}

const STATUS_BG: Record<ViewStatus, string> = {
  draft: "bg-gray-500/15 text-gray-600 dark:text-gray-300",
  in_review: "bg-amber-500/15 text-amber-700 dark:text-amber-300",
  published: "bg-green-500/15 text-green-700 dark:text-green-300",
  deprecated: "bg-red-500/15 text-red-700 dark:text-red-300",
};

const STATUS_LABEL: Record<ViewStatus, string> = {
  draft: "Borrador",
  in_review: "En revisión",
  published: "Publicada",
  deprecated: "Deprecada",
};

export function StatusBadge({ value }: { value: ViewStatus }) {
  return <span className={`badge ${STATUS_BG[value]}`}>{STATUS_LABEL[value]}</span>;
}

const LANG_LABEL: Record<string, string> = { archimate: "ArchiMate", bpmn: "BPMN", uml: "UML" };
export function langLabel(lang: string): string {
  return LANG_LABEL[lang] ?? lang;
}

// Absolute date+time (e.g. "5 ago 2026, 14:30") or "" when the value is missing.
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  return isNaN(d.getTime())
    ? ""
    : d.toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

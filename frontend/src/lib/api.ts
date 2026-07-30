// Thin typed API client. All calls go through the Vite proxy to the backend.
import type {
  Approval,
  Element,
  Finding,
  LayoutNode,
  Registry,
  Relationship,
  View,
  ViewGraph,
} from "./types";

const BASE = "/api/v1";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function qs(params: Record<string, string | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v);
  if (entries.length === 0) return "";
  return "?" + new URLSearchParams(entries as [string, string][]).toString();
}

export const api = {
  registry: () => http<Registry>("/meta/registry"),

  listElements: (f: {
    kind?: string;
    domain?: string;
    lifecycle?: string;
    tag?: string;
    q?: string;
  } = {}) => http<Element[]>(`/elements${qs(f)}`),
  getElement: (slug: string) => http<Element>(`/elements/${slug}`),
  createElement: (body: Partial<Element> & { slug: string; name: string; kind: string }) =>
    http<Element>("/elements", { method: "POST", body: JSON.stringify(body) }),
  updateElement: (slug: string, body: Partial<Element>) =>
    http<Element>(`/elements/${slug}`, { method: "PATCH", body: JSON.stringify(body) }),

  listRelationships: () => http<Relationship[]>("/relationships"),
  createRelationship: (body: { from: string; to: string; kind: string; label?: string }) =>
    http<Relationship>("/relationships", { method: "POST", body: JSON.stringify(body) }),

  listViews: () => http<View[]>("/views"),
  getView: (slug: string) => http<View>(`/views/${slug}`),
  getViewGraph: (slug: string) => http<ViewGraph>(`/views/${slug}/graph`),
  putLayout: (slug: string, nodes: LayoutNode[]) =>
    http<void>(`/views/${slug}/layout`, { method: "PUT", body: JSON.stringify({ nodes }) }),
  addElementsToView: (slug: string, view: View, elements: string[]) => {
    const merged = Array.from(new Set([...view.include.elements, ...elements]));
    return http<View>(`/views/${slug}`, {
      method: "PATCH",
      body: JSON.stringify({ include: { ...view.include, elements: merged } }),
    });
  },

  // Governance (SPEC §11)
  submitReview: (slug: string, approvers: string[], comment?: string) =>
    http<Approval>(`/views/${slug}/submit-review`, {
      method: "POST",
      body: JSON.stringify({ approvers, comment }),
    }),
  publishView: (slug: string) => http<View>(`/views/${slug}/publish`, { method: "POST" }),
  deprecateView: (slug: string) => http<View>(`/views/${slug}/deprecate`, { method: "POST" }),
  listApprovals: (params: { status?: string; mine?: boolean } = {}) =>
    http<Approval[]>(`/approvals${qs({ status: params.status, mine: params.mine ? "true" : undefined })}`),
  approve: (id: string, comment?: string) =>
    http<Approval>(`/approvals/${id}/approve`, { method: "POST", body: JSON.stringify({ comment }) }),
  reject: (id: string, comment?: string) =>
    http<Approval>(`/approvals/${id}/reject`, { method: "POST", body: JSON.stringify({ comment }) }),

  analyze: () => http<Finding[]>("/analysis"),
};

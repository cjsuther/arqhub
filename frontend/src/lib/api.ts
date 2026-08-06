// Thin typed API client. All calls go through the Vite proxy to the backend.
import type {
  AppNotification,
  Approval,
  Comment,
  Element,
  Finding,
  Folder,
  Group,
  LayoutNode,
  ModelDiff,
  Registry,
  Relationship,
  User,
  Version,
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
  addKind: (body: { key: string; layer: string; archimate?: string | null; bpmn?: string | null; uml?: string | null }) =>
    http<Registry>("/meta/kinds", { method: "POST", body: JSON.stringify(body) }),
  deleteKind: (key: string) => http<Registry>(`/meta/kinds/${key}`, { method: "DELETE" }),

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
  updateRelationship: (slug: string, body: { label?: string | null }) =>
    http<Relationship>(`/relationships/${slug}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteRelationship: (slug: string) =>
    http<void>(`/relationships/${slug}`, { method: "DELETE" }),

  listViews: () => http<View[]>("/views"),
  getView: (slug: string) => http<View>(`/views/${slug}`),
  createView: (body: { slug: string; name: string; lang: string; viewpoint?: string }) =>
    http<View>("/views", {
      method: "POST",
      body: JSON.stringify({ ...body, include: { elements: [], relations: "auto" } }),
    }),
  getViewGraph: (slug: string) => http<ViewGraph>(`/views/${slug}/graph`),
  updateViewNotes: (slug: string, notes: string) =>
    http<View>(`/views/${slug}`, { method: "PATCH", body: JSON.stringify({ notes }) }),
  listVersions: (slug: string) => http<Version[]>(`/views/${slug}/versions`),
  createVersion: (slug: string, message: string) =>
    http<Version>(`/views/${slug}/versions`, { method: "POST", body: JSON.stringify({ message }) }),
  diffVersions: (slug: string, from: number, to: number) =>
    http<ModelDiff>(`/views/${slug}/diff${qs({ from: String(from), to: String(to) })}`),
  listComments: (slug: string) => http<Comment[]>(`/views/${slug}/comments`),
  addComment: (slug: string, body: string, mentions: string[] = []) =>
    http<Comment>(`/views/${slug}/comments`, { method: "POST", body: JSON.stringify({ body, mentions }) }),
  deleteComment: (id: string) => http<void>(`/comments/${id}`, { method: "DELETE" }),
  putLayout: (slug: string, nodes: LayoutNode[]) =>
    http<void>(`/views/${slug}/layout`, { method: "PUT", body: JSON.stringify({ nodes }) }),
  addElementsToView: (slug: string, view: View, elements: string[]) => {
    const merged = Array.from(new Set([...view.include.elements, ...elements]));
    return http<View>(`/views/${slug}`, {
      method: "PATCH",
      body: JSON.stringify({ include: { ...view.include, elements: merged } }),
    });
  },
  removeElementFromView: (slug: string, view: View, element: string) => {
    const kept = view.include.elements.filter((e) => e !== element);
    return http<View>(`/views/${slug}`, {
      method: "PATCH",
      body: JSON.stringify({ include: { ...view.include, elements: kept } }),
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

  // Notifications (SPEC §11)
  listNotifications: (unreadOnly = false) =>
    http<AppNotification[]>(`/notifications${qs({ unread_only: unreadOnly ? "true" : undefined })}`),
  unreadCount: () => http<number>("/notifications/unread-count"),
  markNotificationRead: (id: string) => http<void>(`/notifications/${id}/read`, { method: "POST" }),
  markAllNotificationsRead: () => http<void>("/notifications/read-all", { method: "POST" }),

  listUsers: (role?: string) => http<User[]>(`/users${qs({ role })}`),
  getMe: () => http<User>("/users/me"),
  createUser: (body: { email: string; display_name: string; role: string }) =>
    http<User>("/users", { method: "POST", body: JSON.stringify(body) }),
  updateUser: (id: string, body: { role?: string; display_name?: string; email?: string }) =>
    http<User>(`/users/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  setUserGroups: (id: string, ids: string[]) =>
    http<User>(`/users/${id}/groups`, { method: "PUT", body: JSON.stringify({ ids }) }),
  deleteUser: (id: string) => http<void>(`/users/${id}`, { method: "DELETE" }),

  // Groups + folder visibility (SPEC §12)
  listGroups: () => http<Group[]>("/groups"),
  createGroup: (name: string) => http<Group>("/groups", { method: "POST", body: JSON.stringify({ name }) }),
  updateGroup: (id: string, name: string) =>
    http<Group>(`/groups/${id}`, { method: "PATCH", body: JSON.stringify({ name }) }),
  setGroupMembers: (id: string, ids: string[]) =>
    http<Group>(`/groups/${id}/members`, { method: "PUT", body: JSON.stringify({ ids }) }),
  deleteGroup: (id: string) => http<void>(`/groups/${id}`, { method: "DELETE" }),
  getFolderGroups: (folderId: string) => http<string[]>(`/folders/${folderId}/groups`),
  setFolderGroups: (folderId: string, ids: string[]) =>
    http<string[]>(`/folders/${folderId}/groups`, { method: "PUT", body: JSON.stringify({ ids }) }),
  getViewShares: (slug: string) => http<string[]>(`/views/${slug}/shares`),
  setViewShares: (slug: string, ids: string[]) =>
    http<string[]>(`/views/${slug}/shares`, { method: "PUT", body: JSON.stringify({ ids }) }),

  // Folders (SPEC §8.1)
  listFolders: (scope: "element" | "view") => http<Folder[]>(`/folders${qs({ scope })}`),
  createFolder: (body: { name: string; scope: "element" | "view"; parent_id?: string | null }) =>
    http<Folder>("/folders", { method: "POST", body: JSON.stringify(body) }),
  updateFolder: (id: string, body: { name?: string; parent_id?: string | null }) =>
    http<Folder>(`/folders/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteFolder: (id: string) => http<void>(`/folders/${id}`, { method: "DELETE" }),
  setElementFolder: (slug: string, folder_id: string | null) =>
    http<Element>(`/elements/${slug}/folder`, { method: "PATCH", body: JSON.stringify({ folder_id }) }),
  setViewFolder: (slug: string, folder_id: string | null) =>
    http<View>(`/views/${slug}/folder`, { method: "PATCH", body: JSON.stringify({ folder_id }) }),
};

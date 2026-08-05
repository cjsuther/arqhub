// Domain types mirroring the backend API schemas (SPEC §7).
// TODO: replace with an OpenAPI-generated client once the API stabilises (§15).

export type Lang = "archimate" | "bpmn" | "uml";
export type Lifecycle = "proposed" | "active" | "deprecated" | "retired";
export type ViewStatus = "draft" | "in_review" | "published" | "deprecated";

export interface Element {
  slug: string;
  name: string;
  kind: string;
  domain: string | null;
  owner: string | null;
  description: string | null;
  lifecycle: Lifecycle;
  tags: string[];
  properties: Record<string, string>;
  mappings: Record<string, string>;
  folder_id: string | null;
}

export interface Folder {
  id: string;
  name: string;
  scope: "element" | "view";
  parent_id: string | null;
}

export interface Relationship {
  slug: string;
  from: string;
  to: string;
  kind: string;
  label: string | null;
  properties: Record<string, string>;
}

export interface View {
  slug: string;
  name: string;
  lang: Lang;
  viewpoint: string | null;
  include: { elements: string[]; relations: string[] | "auto" };
  status: ViewStatus;
  status_changed_at: string | null;
  status_changed_by: string | null;
  status_changed_by_name: string | null;
  created_by: string | null;
  created_by_name: string | null;
  current_version: number;
  folder_id: string | null;
  notes: string | null;
}

export interface Version {
  version: number;
  scope: string;
  scope_id: string | null;
  message: string | null;
}

export interface FieldChange {
  field: string;
  before: unknown;
  after: unknown;
}
export interface ModifiedEntry {
  id: string;
  changes: FieldChange[];
}
export interface EntityDiff {
  added: string[];
  removed: string[];
  modified: ModifiedEntry[];
}
export interface ModelDiff {
  elements: EntityDiff;
  relations: EntityDiff;
  views: EntityDiff;
}

export interface Comment {
  id: string;
  body: string;
  author_id: string | null;
  author_name: string | null;
  created_at: string;
}

export interface RegistryKind {
  layer: string;
  mappings: Record<Lang, string | null>;
  custom?: boolean;
}

export interface Registry {
  langs: Lang[];
  lifecycles: Lifecycle[];
  kinds: Record<string, RegistryKind>;
  relations: Record<string, Record<Lang, string | null>>;
  relation_aliases: Record<string, string>;
}

export interface LayoutNode {
  element: string;
  x: number;
  y: number;
  w: number;
  h: number;
  parent?: string | null;
  style: Record<string, unknown>;
}

export interface ViewGraph {
  view: View;
  elements: Element[];
  relations: Relationship[];
  layout: LayoutNode[];
}

export type Role = "viewer" | "editor" | "approver" | "admin";

export interface GroupRef {
  id: string;
  name: string;
}

export interface Group {
  id: string;
  name: string;
  member_count: number;
  folder_ids: string[];
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  is_entra?: boolean;
  groups: GroupRef[];
}

export interface Finding {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
  entities: string[];
  suggestion: string | null;
}

export interface ApprovalDecision {
  approver_id: string | null;
  approver_name: string | null;
  decision: "approved" | "rejected";
  comment: string;
  decided_at: string;
}

export interface Approval {
  id: string;
  view_slug: string;
  view_version: number;
  view_status: ViewStatus;
  status: "pending" | "approved" | "rejected" | "cancelled";
  created_at: string;
  requested_by: string | null;
  requested_by_name: string | null;
  approvers: string[];
  approver_names: string[];
  decisions: ApprovalDecision[];
  resolved_by: string | null;
  resolved_by_name: string | null;
  resolved_at: string | null;
  comment: string | null;
}

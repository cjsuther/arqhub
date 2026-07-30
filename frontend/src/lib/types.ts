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
  current_version: number;
}

export interface RegistryKind {
  layer: "business" | "application" | "technology" | "motivation";
  mappings: Record<Lang, string | null>;
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
  style: Record<string, unknown>;
}

export interface ViewGraph {
  view: View;
  elements: Element[];
  relations: Relationship[];
  layout: LayoutNode[];
}

export interface Finding {
  code: string;
  severity: "info" | "warning" | "error";
  message: string;
  entities: string[];
  suggestion: string | null;
}

export interface Approval {
  id: string;
  view_slug: string;
  view_version: number;
  status: "pending" | "approved" | "rejected" | "cancelled";
  requested_by: string | null;
  approvers: string[];
  resolved_by: string | null;
  comment: string | null;
}

import { describe, expect, it } from "vitest";

import type { Element, FieldDef } from "../../lib/types";
import { buildQuery, fieldTokenMap, matchElement, parseQuery } from "./search";

const el = (over: Partial<Element>): Element => ({
  slug: "x", name: "X", kind: "actor", domain: null, owner: null, description: null,
  lifecycle: "active", tags: [], properties: {}, mappings: {}, custom_fields: {}, folder_id: null,
  ...over,
});

const fd = (over: Partial<FieldDef> & { key: string; field_type: FieldDef["field_type"] }): FieldDef => ({
  id: over.key, kind: "actor", label: over.key, options: [], position: 0, ...over,
});

const FIELDS: FieldDef[] = [
  fd({ key: "fecha-vencimiento", label: "Fecha de vencimiento", field_type: "date" }),
  fd({ key: "monto", field_type: "number" }),
  fd({ key: "prioridad", field_type: "select", options: ["alta", "baja"] }),
  fd({ key: "team", field_type: "text" }),
  fd({ key: "etiquetas", field_type: "multiselect", options: ["a", "b", "c"] }),
];
const tokens = fieldTokenMap(FIELDS);

describe("parseQuery", () => {
  it("splits free text from field clauses", () => {
    const pq = parseQuery("hola team:pagos mundo", tokens);
    expect(pq.text).toBe("hola mundo");
    expect(pq.clauses).toEqual([{ token: "team", op: "eq", value: "pagos" }]);
  });

  it("parses ranges and open-ended bounds", () => {
    expect(parseQuery("monto:10..20", tokens).clauses[0]).toEqual({ token: "monto", op: "range", value: "", from: "10", to: "20" });
    expect(parseQuery("monto:10..", tokens).clauses[0]).toMatchObject({ op: "range", from: "10", to: "" });
    expect(parseQuery("monto:..20", tokens).clauses[0]).toMatchObject({ op: "range", from: "", to: "20" });
  });

  it("parses comparison operators", () => {
    expect(parseQuery("monto:>=100", tokens).clauses[0]).toEqual({ token: "monto", op: "gte", value: "100" });
    expect(parseQuery("monto:<5", tokens).clauses[0]).toEqual({ token: "monto", op: "lt", value: "5" });
  });

  it("accepts the field label (not only the key) and quoted values", () => {
    const pq = parseQuery('"Fecha de vencimiento":2026-08-20 team:"mesa de ayuda"', tokens);
    expect(pq.clauses).toContainEqual({ token: "fecha de vencimiento", op: "eq", value: "2026-08-20" });
    expect(pq.clauses).toContainEqual({ token: "team", op: "eq", value: "mesa de ayuda" });
  });

  it("treats unknown tokens and empty values as free text", () => {
    const pq = parseQuery("http://x.y desconocido:z team:", tokens);
    expect(pq.clauses).toEqual([]);
    expect(pq.text).toContain("http://x.y");
    expect(pq.text).toContain("desconocido:z");
  });

  it("recognises reserved tipo/ciclo tokens", () => {
    const pq = parseQuery("tipo:actor ciclo:active", tokens);
    expect(pq.clauses).toEqual([
      { token: "tipo", op: "eq", value: "actor" },
      { token: "ciclo", op: "eq", value: "active" },
    ]);
  });
});

describe("matchElement", () => {
  const run = (q: string, e: Element) => matchElement(e, parseQuery(q, tokens), tokens);

  it("matches free text over name, description and custom values", () => {
    const e = el({ name: "Cliente", description: "solicita alta", custom_fields: { team: "Pagos" } });
    expect(run("cliente", e)).toBe(true);
    expect(run("alta", e)).toBe(true);
    expect(run("pagos", e)).toBe(true);
    expect(run("inexistente", e)).toBe(false);
  });

  it("filters dates by inclusive range", () => {
    const e = el({ custom_fields: { "fecha-vencimiento": "2026-08-20" } });
    expect(run("fecha-vencimiento:2026-08-01..2026-08-31", e)).toBe(true);
    expect(run("fecha-vencimiento:2026-08-20..2026-08-20", e)).toBe(true);
    expect(run("fecha-vencimiento:2026-09-01..2026-09-30", e)).toBe(false);
  });

  it("compares numbers numerically, not lexicographically", () => {
    const e = el({ custom_fields: { monto: 100 } });
    expect(run("monto:>=90", e)).toBe(true);
    expect(run("monto:9..100", e)).toBe(true); // lexical "100" < "9" would fail; numeric passes
    expect(run("monto:<90", e)).toBe(false);
  });

  it("does substring eq for text/select and any-of for multiselect", () => {
    expect(run("team:pag", el({ custom_fields: { team: "Pagos" } }))).toBe(true);
    expect(run("prioridad:alta", el({ custom_fields: { prioridad: "alta" } }))).toBe(true);
    expect(run("etiquetas:b", el({ custom_fields: { etiquetas: ["a", "b"] } }))).toBe(true);
    expect(run("etiquetas:z", el({ custom_fields: { etiquetas: ["a", "b"] } }))).toBe(false);
  });

  it("matches reserved tipo/ciclo exactly and combines clauses (AND)", () => {
    const e = el({ kind: "actor", lifecycle: "active", custom_fields: { "fecha-vencimiento": "2026-08-20" } });
    expect(run("tipo:actor", e)).toBe(true);
    expect(run("tipo:role", e)).toBe(false);
    expect(run("tipo:actor fecha-vencimiento:2026-08-01..2026-08-31", e)).toBe(true);
    expect(run("tipo:role fecha-vencimiento:2026-08-01..2026-08-31", e)).toBe(false);
  });

  it("excludes elements missing the field", () => {
    expect(run("team:pagos", el({ custom_fields: {} }))).toBe(false);
  });
});

describe("buildQuery", () => {
  it("composes free text and field tokens, quoting values with spaces", () => {
    const q = buildQuery("cliente nuevo", [
      { token: "tipo", value: "actor" },
      { token: "team", value: "mesa de ayuda" },
    ]);
    expect(q).toBe('cliente nuevo tipo:actor team:"mesa de ayuda"');
  });

  it("builds ranges and open-ended bounds, skipping empty parts", () => {
    const q = buildQuery("", [
      { token: "fecha-vencimiento", from: "2026-08-01", to: "2026-08-31" },
      { token: "monto", from: "10", to: "" },
      { token: "prioridad", value: "" },
    ]);
    expect(q).toBe("fecha-vencimiento:2026-08-01..2026-08-31 monto:10..");
  });

  it("round-trips through parseQuery", () => {
    const q = buildQuery("", [{ token: "fecha-vencimiento", from: "2026-08-01", to: "2026-08-31" }]);
    const pq = parseQuery(q, tokens);
    expect(pq.clauses[0]).toMatchObject({ token: "fecha-vencimiento", op: "range", from: "2026-08-01", to: "2026-08-31" });
  });
});

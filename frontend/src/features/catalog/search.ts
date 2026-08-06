// Client-side query language for the catalog search box.
//
// A query is free text plus zero or more `field:value` clauses. Field tokens are a
// custom field's key (or label), or the reserved `tipo`/`ciclo`. Values support
// ranges (`a..b`, open-ended `a..` / `..b`) and comparisons (`>=`, `<=`, `>`, `<`),
// which is what makes dates and numbers searchable by range. Anything that isn't a
// recognised `field:value` token is treated as free text over name/description/values.

import type { Element, FieldDef } from "../../lib/types";

export type Op = "eq" | "range" | "gte" | "lte" | "gt" | "lt";

export interface Clause {
  token: string; // normalised field token (lowercased key/label, or reserved)
  op: Op;
  value: string; // for eq/gte/lte/gt/lt
  from?: string; // range lower bound
  to?: string; // range upper bound
}

export interface ParsedQuery {
  text: string;
  clauses: Clause[];
}

const RESERVED: Record<string, "kind" | "lifecycle"> = {
  tipo: "kind", kind: "kind",
  ciclo: "lifecycle", lifecycle: "lifecycle", estado: "lifecycle",
};

/** Map every token a user can type (field key + label, lowercased) to its FieldDef. */
export function fieldTokenMap(fields: FieldDef[]): Map<string, FieldDef> {
  const m = new Map<string, FieldDef>();
  for (const f of fields) {
    m.set(f.key.toLowerCase(), f);
    m.set(f.label.toLowerCase(), f);
  }
  return m;
}

// Split on whitespace but keep double-quoted spans intact, even mid-token
// (`team:"mesa de ayuda"` and `"Fecha de vencimiento":2026-08-20` stay one token).
function tokenize(raw: string): string[] {
  const out: string[] = [];
  let cur = "";
  let inQuote = false;
  for (const ch of raw) {
    if (ch === '"') {
      inQuote = !inQuote;
      cur += ch;
    } else if (/\s/.test(ch) && !inQuote) {
      if (cur) { out.push(cur); cur = ""; }
    } else {
      cur += ch;
    }
  }
  if (cur) out.push(cur);
  return out;
}

function unquote(s: string): string {
  return s.length >= 2 && s.startsWith('"') && s.endsWith('"') ? s.slice(1, -1) : s;
}

function makeClause(token: string, value: string): Clause {
  if (value.includes("..")) {
    const [from, to] = value.split("..");
    return { token, op: "range", value: "", from, to };
  }
  const m = value.match(/^(>=|<=|>|<)(.*)$/);
  if (m) {
    const op: Op = m[1] === ">=" ? "gte" : m[1] === "<=" ? "lte" : m[1] === ">" ? "gt" : "lt";
    return { token, op, value: m[2] };
  }
  return { token, op: "eq", value };
}

function isEmpty(c: Clause): boolean {
  if (c.op === "range") return !c.from && !c.to;
  return c.value === "";
}

export function parseQuery(raw: string, tokens: Map<string, FieldDef>): ParsedQuery {
  const clauses: Clause[] = [];
  const text: string[] = [];
  for (const tok of tokenize(raw)) {
    const i = tok.indexOf(":");
    if (i > 0) {
      const key = unquote(tok.slice(0, i)).toLowerCase();
      if (tokens.has(key) || key in RESERVED) {
        const c = makeClause(key, unquote(tok.slice(i + 1)));
        if (!isEmpty(c)) { clauses.push(c); continue; }
      }
    }
    text.push(unquote(tok));
  }
  return { text: text.join(" ").trim(), clauses };
}

function cmp(a: string, b: string, numeric: boolean): number {
  if (numeric) {
    const x = Number(a), y = Number(b);
    if (Number.isNaN(x) || Number.isNaN(y)) return NaN;
    return x - y;
  }
  return a < b ? -1 : a > b ? 1 : 0;
}

function valueMatches(s: string, c: Clause, type: FieldDef["field_type"]): boolean {
  const numeric = type === "number";
  switch (c.op) {
    case "eq":
      if (numeric) {
        const t = Number(c.value);
        return Number.isNaN(t) ? s.toLowerCase().includes(c.value.toLowerCase()) : Number(s) === t;
      }
      return s.toLowerCase().includes(c.value.toLowerCase());
    case "gte": { const r = cmp(s, c.value, numeric); return !Number.isNaN(r) && r >= 0; }
    case "lte": { const r = cmp(s, c.value, numeric); return !Number.isNaN(r) && r <= 0; }
    case "gt": { const r = cmp(s, c.value, numeric); return !Number.isNaN(r) && r > 0; }
    case "lt": { const r = cmp(s, c.value, numeric); return !Number.isNaN(r) && r < 0; }
    case "range": {
      if (c.from) { const r = cmp(s, c.from, numeric); if (Number.isNaN(r) || r < 0) return false; }
      if (c.to) { const r = cmp(s, c.to, numeric); if (Number.isNaN(r) || r > 0) return false; }
      return true;
    }
  }
}

function clauseMatches(el: Element, c: Clause, tokens: Map<string, FieldDef>): boolean {
  const reserved = RESERVED[c.token];
  if (reserved === "kind") return c.op === "eq" && el.kind.toLowerCase() === c.value.toLowerCase();
  if (reserved === "lifecycle") return c.op === "eq" && el.lifecycle.toLowerCase() === c.value.toLowerCase();
  const field = tokens.get(c.token);
  if (!field) return true;
  const raw = (el.custom_fields ?? {})[field.key];
  const arr = Array.isArray(raw) ? raw : raw == null || raw === "" ? [] : [raw];
  if (arr.length === 0) return false;
  return arr.some((v) => valueMatches(String(v), c, field.field_type));
}

export function matchElement(el: Element, pq: ParsedQuery, tokens: Map<string, FieldDef>): boolean {
  if (pq.text) {
    const cf = el.custom_fields ?? {};
    const extra = Object.values(cf).flatMap((v) => (Array.isArray(v) ? v : [v])).map(String).join(" ");
    const hay = `${el.slug} ${el.name} ${el.description ?? ""} ${extra}`.toLowerCase();
    if (!hay.includes(pq.text.toLowerCase())) return false;
  }
  return pq.clauses.every((c) => clauseMatches(el, c, tokens));
}

export interface QueryPart {
  token: string;
  value?: string;
  from?: string;
  to?: string;
}

const needsQuote = (v: string) => /\s/.test(v);

/** Compose a query string from the advanced-search dialog state. */
export function buildQuery(text: string, parts: QueryPart[]): string {
  const toks: string[] = [];
  if (text.trim()) toks.push(text.trim());
  for (const p of parts) {
    let v: string;
    if (p.from != null || p.to != null) {
      const f = p.from ?? "", t = p.to ?? "";
      if (!f && !t) continue;
      v = `${f}..${t}`;
    } else if (p.value != null && p.value !== "") {
      v = needsQuote(p.value) ? `"${p.value}"` : p.value;
    } else {
      continue;
    }
    toks.push(`${p.token}:${v}`);
  }
  return toks.join(" ");
}

// Allowlist HTML sanitiser for rendering user-authored rich text (view docs).
// The backend sanitises on write; this is defense-in-depth for data stored before
// that existed and for anything rendered via dangerouslySetInnerHTML. Browser-only
// (uses the DOM). Mirrors app/services/html_sanitize.py.

const ALLOWED = new Set([
  "H1", "H2", "H3", "H4", "P", "BR", "B", "STRONG", "I", "EM", "U", "S",
  "UL", "OL", "LI", "A", "SPAN", "DIV", "BLOCKQUOTE", "CODE", "PRE",
]);
const SAFE_HREF = /^(https?:|mailto:|\/|#)/;

function processNode(node: ChildNode): void {
  if (node.nodeType === 8) { node.remove(); return; } // comment
  if (node.nodeType !== 1) return; // text: keep as-is (browser already escapes)
  const el = node as Element;

  if (!ALLOWED.has(el.tagName)) {
    // Unwrap disallowed element: keep its children, drop the tag (and its attrs).
    const moved = Array.from(el.childNodes);
    el.replaceWith(...moved);
    moved.forEach(processNode);
    return;
  }

  for (const attr of Array.from(el.attributes)) {
    const name = attr.name.toLowerCase();
    if (el.tagName === "A" && name === "href") {
      const v = attr.value.trim().toLowerCase();
      if (!SAFE_HREF.test(v) || v.includes("javascript:")) el.removeAttribute(attr.name);
    } else {
      el.removeAttribute(attr.name); // strips on*, style, src, etc.
    }
  }
  if (el.tagName === "A") {
    el.setAttribute("target", "_blank");
    el.setAttribute("rel", "noopener noreferrer");
  }
  Array.from(el.childNodes).forEach(processNode);
}

export function sanitizeHtml(dirty: string): string {
  if (!dirty) return "";
  const tpl = document.createElement("template");
  tpl.innerHTML = dirty;
  Array.from(tpl.content.childNodes).forEach(processNode);
  return tpl.innerHTML;
}

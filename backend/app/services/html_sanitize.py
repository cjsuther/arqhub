"""Allowlist HTML sanitiser for user-authored rich text (view documentation).

The view "notes" are edited with a contentEditable WYSIWYG and rendered with
``dangerouslySetInnerHTML`` in the SPA, so raw HTML there is a stored-XSS vector.
This strips everything except a small allowlist of formatting tags, drops all
attributes (only safe ``href`` on ``<a>`` survives) and removes ``<script>`` /
``<style>`` content entirely. Stdlib only — no bleach/lxml (corporate npm/pip
proxy friendly). Authoritative: applied on write, regardless of the client.
"""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser

_ALLOWED_TAGS = {
    "h1", "h2", "h3", "h4", "p", "br", "b", "strong", "i", "em", "u", "s",
    "ul", "ol", "li", "a", "span", "div", "blockquote", "code", "pre",
}
_VOID_TAGS = {"br"}
_DROP_WITH_CONTENT = {"script", "style"}
_SAFE_URL_PREFIXES = ("http://", "https://", "mailto:", "/", "#")


def _safe_href(value: str) -> str | None:
    v = value.strip()
    low = v.lower()
    if "javascript:" in low or low.startswith("data:"):
        return None
    return v if low.startswith(_SAFE_URL_PREFIXES) else None


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self._skip = 0  # depth inside a drop-with-content tag

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _DROP_WITH_CONTENT:
            self._skip += 1
            return
        if self._skip or tag not in _ALLOWED_TAGS:
            return  # disallowed tag is unwrapped: its children/text are kept
        if tag == "a":
            href = _safe_href(dict(attrs).get("href") or "")
            self.out.append(
                f'<a href="{escape(href, quote=True)}" target="_blank" rel="noopener noreferrer">'
                if href else "<a>"
            )
        else:
            self.out.append(f"<{tag}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self._skip and tag in _ALLOWED_TAGS and tag != "a":
            self.out.append(f"<{tag}>")

    def handle_endtag(self, tag: str) -> None:
        if tag in _DROP_WITH_CONTENT:
            self._skip = max(0, self._skip - 1)
            return
        if self._skip or tag not in _ALLOWED_TAGS or tag in _VOID_TAGS:
            return
        self.out.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.out.append(escape(data, quote=False))


def sanitize_html(dirty: str | None) -> str:
    if not dirty:
        return ""
    p = _Sanitizer()
    p.feed(dirty)
    p.close()
    return "".join(p.out)

"""ArqHub MCP server (SPEC §9).

Exposes the ArqHub model to LLMs as tools over MCP. Every tool wraps a REST
endpoint. Transports: stdio (local, e.g. Claude Code) and streamable HTTP.

Security (SPEC §9): the IA can search, read, create/edit drafts and *request*
approval — it can NOT approve, reject, publish or cascade-delete, so those tools
are deliberately absent. Every mutation is audited server-side as actor_type=mcp.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .client import ArqHubClient

mcp = FastMCP("arqhub")
api = ArqHubClient()


# --- Read / query ------------------------------------------------------------
@mcp.tool()
def search_catalog(q: str = "", kind: str = "", domain: str = "") -> list[dict]:
    """Search elements by text/kind/domain. Returns slugs + summaries."""
    return api.get("/elements", {"q": q or None, "kind": kind or None, "domain": domain or None})


@mcp.tool()
def get_element(slug: str) -> dict:
    """Full element card plus the views where it appears."""
    element = api.get(f"/elements/{slug}")
    return {"element": element, "views": api.get(f"/elements/{slug}/views")}


@mcp.tool()
def query_model(slug: str, depth: int = 2, directed: bool = True) -> dict:
    """Structural query: impact graph (BFS) around an element."""
    return api.get(f"/elements/{slug}/impact", {"depth": depth, "directed": directed})


@mcp.tool()
def export_dsl() -> str:
    """Export the whole model as DSL YAML."""
    return api.get("/dsl/export")


@mcp.tool()
def import_dsl(dsl_yaml: str, dry_run: bool = True) -> dict:
    """Apply a DSL document (model or patch). dry_run validates without persisting."""
    return api.post("/dsl/import", params={"dry_run": dry_run}, content=dsl_yaml)


# --- Create / edit drafts ----------------------------------------------------
@mcp.tool()
def create_element(slug: str, name: str, kind: str, domain: str = "", description: str = "") -> dict:
    """Create a catalog element."""
    return api.post("/elements", json={
        "slug": slug, "name": name, "kind": kind,
        "domain": domain or None, "description": description or None,
    })


@mcp.tool()
def update_element(slug: str, name: str = "", description: str = "", lifecycle: str = "") -> dict:
    """Update an element (only provided fields)."""
    body = {k: v for k, v in {"name": name, "description": description, "lifecycle": lifecycle}.items() if v}
    return api.patch(f"/elements/{slug}", body)


@mcp.tool()
def create_relationship(from_slug: str, to_slug: str, kind: str, label: str = "") -> dict:
    """Create a relationship (validated against the type matrix)."""
    return api.post("/relationships", json={
        "from": from_slug, "to": to_slug, "kind": kind, "label": label or None,
    })


@mcp.tool()
def generate_view(slug: str, name: str, lang: str, elements: list[str]) -> dict:
    """Create a draft view of the given language over a list of elements."""
    return api.post("/views", json={
        "slug": slug, "name": name, "lang": lang,
        "include": {"elements": elements, "relations": "auto"},
    })


# --- Views / versions --------------------------------------------------------
@mcp.tool()
def get_view(slug: str) -> dict:
    """View metadata + resolved graph + layout."""
    return api.get(f"/views/{slug}/graph")


@mcp.tool()
def render_view(slug: str) -> str:
    """SVG rendering of a view."""
    return api.get(f"/views/{slug}/render")


@mcp.tool()
def export_view_mermaid(slug: str) -> str:
    """Mermaid flowchart of a view — compact text the IA can read/understand fast."""
    return api.get("/export/mermaid", {"view": slug})


@mcp.tool()
def diff_versions(slug: str, from_version: int, to_version: int) -> dict:
    """Semantic diff between two versions of a view."""
    return api.get(f"/views/{slug}/diff", {"from": from_version, "to": to_version})


# --- Governance (request only) + analysis ------------------------------------
@mcp.tool()
def request_approval(slug: str, approvers: list[str], comment: str = "") -> dict:
    """Submit a view for review. The IA can request but never approve/publish."""
    return api.post(f"/views/{slug}/submit-review", json={"approvers": approvers, "comment": comment or None})


@mcp.tool()
def get_approval_status(status: str = "") -> list[dict]:
    """List approval requests (optionally filtered by status)."""
    return api.get("/approvals", {"status": status or None})


@mcp.tool()
def propose_optimization() -> list[dict]:
    """Run the deterministic analysis rules and return structured findings (§10)."""
    return api.get("/analysis")


@mcp.tool()
def list_folders(scope: str = "element") -> list[dict]:
    """List folders of a scope ('element' | 'view')."""
    return api.get("/folders", {"scope": scope})


@mcp.tool()
def create_folder(name: str, scope: str = "element", parent_id: str = "") -> dict:
    """Create a folder ('element' | 'view'). parent_id empty = root."""
    return api.post("/folders", json={"name": name, "scope": scope, "parent_id": parent_id or None})


@mcp.tool()
def move_element_to_folder(slug: str, folder_id: str = "") -> dict:
    """Move a component into a folder (empty folder_id = no folder)."""
    return api.patch(f"/elements/{slug}/folder", {"folder_id": folder_id or None})


@mcp.tool()
def move_view_to_folder(slug: str, folder_id: str = "") -> dict:
    """Move a view into a folder (empty folder_id = no folder)."""
    return api.patch(f"/views/{slug}/folder", {"folder_id": folder_id or None})


@mcp.tool()
def add_elements_to_view(slug: str, elements: list[str]) -> dict:
    """Add existing components to a view (merged with its current include set)."""
    view = api.get(f"/views/{slug}")
    include = view.get("include") or {"elements": [], "relations": "auto"}
    merged = list(dict.fromkeys([*include.get("elements", []), *elements]))
    return api.patch(f"/views/{slug}", {"include": {**include, "elements": merged}})


def main() -> None:
    """Run the server.

    Default transport is stdio (Claude Code launches the process). Set
    ARQHUB_MCP_TRANSPORT=http to run a pre-started streamable-HTTP server instead
    — useful on slow machines where per-launch cold start exceeds the client's
    startup timeout. Then point the client at http://host:port/mcp.
    """
    import os

    transport = os.environ.get("ARQHUB_MCP_TRANSPORT", "stdio").lower()
    if transport in ("http", "streamable-http", "sse"):
        mcp.settings.host = os.environ.get("ARQHUB_MCP_HOST", "127.0.0.1")
        mcp.settings.port = int(os.environ.get("ARQHUB_MCP_PORT", "8931"))
        mcp.run(transport="sse" if transport == "sse" else "streamable-http")
    else:
        mcp.run()


if __name__ == "__main__":
    main()

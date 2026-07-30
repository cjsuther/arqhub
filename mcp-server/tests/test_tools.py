"""MCP tool registration + the §9 security invariant.

Run: PYTHONPATH=src pytest  (requires `mcp` and `httpx` installed)."""

import asyncio

from arqhub_mcp import server

EXPECTED = {
    "search_catalog", "get_element", "query_model", "export_dsl", "import_dsl",
    "create_element", "update_element", "create_relationship", "generate_view",
    "get_view", "render_view", "diff_versions", "request_approval",
    "get_approval_status", "propose_optimization",
}
# The IA must never be able to approve/publish/delete (SPEC §9).
FORBIDDEN = {"approve", "reject", "publish", "deprecate", "delete_element", "delete_relationship"}


def _tool_names() -> set[str]:
    tools = asyncio.run(server.mcp.list_tools())
    return {t.name for t in tools}


def test_expected_tools_registered():
    assert EXPECTED <= _tool_names()


def test_no_forbidden_tools_exposed():
    assert not (_tool_names() & FORBIDDEN)

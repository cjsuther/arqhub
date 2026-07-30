# ArqHub MCP server

Expone el modelo de ArqHub a los LLMs como **tools MCP** (SPEC §9). Cada tool
envuelve un endpoint de la API REST; toda mutación queda auditada como
`actor_type=mcp`.

## Seguridad (SPEC §9)

La IA puede **buscar, leer, crear/editar drafts y solicitar aprobación**. **No**
puede aprobar, rechazar, publicar ni borrar en cascada — esas tools no existen.

## Tools

`search_catalog`, `get_element`, `query_model`, `export_dsl`, `import_dsl`,
`create_element`, `update_element`, `create_relationship`, `generate_view`,
`get_view`, `render_view`, `diff_versions`, `request_approval`,
`get_approval_status`, `propose_optimization`.

## Correr

```bash
cd mcp-server
python -m venv .venv && ./.venv/Scripts/python -m pip install -e .
# Config: apunta a la API y (opcional) un PAT
export ARQHUB_API=http://localhost:8000/api/v1
export ARQHUB_PAT=<token>            # en dev no hace falta (auth stub)
arqhub-mcp                            # transporte stdio (Claude Code)
```

Para Claude Code, en `.mcp.json` / config de MCP:

```json
{ "mcpServers": { "arqhub": { "command": "arqhub-mcp" } } }
```

Transporte HTTP remoto: usar `mcp.run_streamable_http_async()` en `server.py`.

## Tests

```bash
cd mcp-server && PYTHONPATH=src pytest
```

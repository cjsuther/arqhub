# Levanta el servidor MCP de ArqHub en modo HTTP (streamable) en :8931.
# Requiere el backend corriendo en :8000 (dev.ps1). Dejá esta ventana abierta;
# Claude Code se conecta por http://127.0.0.1:8931/mcp (ver .mcp.json).
$ErrorActionPreference = "Stop"
$env:ARQHUB_MCP_TRANSPORT = "http"
$env:ARQHUB_MCP_HOST = "127.0.0.1"
$env:ARQHUB_MCP_PORT = "8931"
$env:ARQHUB_API = "http://localhost:8000/api/v1"

Write-Host "Servidor MCP ArqHub (HTTP) en http://127.0.0.1:8931/mcp ..." -ForegroundColor Cyan
& "$PSScriptRoot\backend\.venv\Scripts\python.exe" -m arqhub_mcp.server

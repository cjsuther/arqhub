# Levanta ArqHub en local: backend (FastAPI :8000) + frontend (Vite :5173).
# Uso:  ./dev.ps1        (desde la carpeta ArqHub, en PowerShell)
# Cada servidor abre en su propia ventana; cerrala para frenarlo.

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host "Iniciando backend (FastAPI) en http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\backend'; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"
)

Write-Host "Iniciando frontend (Vite) en http://localhost:5173 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "cd '$root\frontend'; npm run dev"
)

Start-Sleep -Seconds 3
Write-Host ""
Write-Host "Abriendo http://localhost:5173 ..." -ForegroundColor Green
Start-Process "http://localhost:5173"

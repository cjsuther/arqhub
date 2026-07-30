# ArqHub

Plataforma web **model-first / IA-first** para crear, navegar, versionar y publicar diagramas
**ArchiMate, BPMN y UML** sobre un **repositorio semántico único** (metamodelo propio), con la IA
como usuario de primera clase (vía MCP).

El corazón no son los diagramas: es el catálogo semántico. Un elemento (ej. "API de Pagos") se
define **una sola vez** y se proyecta a cada lenguaje; los diagramas son **vistas** del modelo.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · Pydantic v2 |
| DB | PostgreSQL 16 (dev: SQLite, sin infra) · Redis + arq (jobs) |
| Frontend | React 18 · TypeScript · Vite · React Flow · ELK.js · Tailwind · TanStack Query |
| Auth | Entra ID (Azure AD) OIDC detrás de una interfaz `AuthProvider` |
| DSL | YAML IA-first (import/export, diff semántico) |

## Estado

- **Fase 1 — Núcleo del repositorio + DSL** ✅ — motor DSL (parser/validator/importer model+patch/
  exporter/diff), API REST `/api/v1`, modelos + migraciones, Entra ID OIDC, jobs arq (snapshot diario),
  RLS Postgres. 38 tests.
- **Fase 2 — Canvas ArchiMate + catálogo** ✅ — app shell, catálogo con fichas navegables, explorador
  de vistas, y **editor canvas React Flow** (custom nodes/edges ArchiMate, ELK auto-layout, paleta,
  panel de propiedades, persistencia de layout).
- **Fases 3–6** ⏳ — BPMN/UML + exportadores estándar, governance + Teams, MCP + análisis, hardening.

## Cómo correr en local

Requisitos: Python 3.12+, Node 20+. (Postgres/Redis opcionales — dev usa SQLite y jobs inline.)

```bash
# Backend
cd backend
python -m venv .venv
./.venv/Scripts/python -m pip install -e ".[dev]"   # (Linux/mac: .venv/bin/python)
./.venv/Scripts/python -m uvicorn app.main:app --reload   # API en :8000, docs en /docs

# Frontend (otra terminal)
cd frontend
npm install
npm run dev                                          # UI en :5173 (proxy /api -> :8000)
```

En Windows: `./dev.ps1` levanta ambos y abre el navegador.

Con Postgres/Redis: `docker compose up`.

## Tests

```bash
cd backend && ./.venv/Scripts/python -m pytest -q
```

## Documentación

- [`defs/SPEC-plataforma-diagramas.md`](defs/SPEC-plataforma-diagramas.md) — especificación completa.
- [`docs/archimate-notation.md`](docs/archimate-notation.md) — referencia de notación ArchiMate para el canvas.
- [`CLAUDE.md`](CLAUDE.md) — convenciones de desarrollo.

## Licencia

Sin licencia definida aún (todos los derechos reservados por defecto). El material de referencia de
terceros con copyright (p. ej. el excerpt de *Mastering ArchiMate*) **no** se incluye en el repositorio.

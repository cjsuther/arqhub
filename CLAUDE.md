# ArqHub — convenciones para Claude Code

Plataforma de Arquitectura Empresarial **model-first / IA-first**: repositorio semántico único
(metamodelo propio) del que se proyectan vistas ArchiMate, BPMN y UML. La spec completa está en
[`defs/SPEC-plataforma-diagramas.md`](defs/SPEC-plataforma-diagramas.md); este archivo son las reglas
operativas (§15 de la spec).

## Idioma

- **Código e identificadores en inglés.** UI y documentación de usuario **en español**.
- Comentarios: en el idioma que aclare mejor; los docstrings de dominio pueden citar la spec (`SPEC §X`).

## Backend (Python 3.12 + FastAPI)

- Type hints obligatorios. Pydantic para **todo** I/O.
- Sin lógica de negocio en los routers: vive en `app/services/`.
- Tests pytest por servicio: mínimo happy path + 2 edge cases.
- Todo cambio de modelo de datos → migración Alembic con `downgrade` funcional.
- La **matriz de tipos/relaciones (SPEC §4.2) es fuente única de verdad** y vive en
  [`backend/app/services/dsl/registry.py`](backend/app/services/dsl/registry.py). Nada más define esos
  mapeos; el front la consume por `GET /api/v1/meta/registry`.

## DSL (el formato IA-first, SPEC §5)

- La capa DSL (`app/services/dsl/`) es **pura y sin DB**: opera sobre `ModelGraph` en memoria, así se
  testea sin Postgres. La persistencia mapea filas ⇆ `ModelGraph` en la capa de repositorio.
- **Sin coordenadas en el DSL.** El layout es presentación (tabla `view_layouts`), nunca modelo.
- Roundtrip garantizado semánticamente: `load(export(g)) == g`. Los alias de relación (`uses`→`serving`,
  `flow`→`triggering`) se normalizan al importar; el export emite el token canónico.
- Toda importación devuelve reporte estructurado (errores + warnings + diff) para que un LLM se
  autocorrija. Hard violations = error; desajustes de la matriz por lenguaje = warning (no bloquean).

## Frontend (React 18 + TS + Vite)

- Componentes funcionales, sin `any`. Estado global solo en stores Zustand por feature.
- Llamadas API **solo** vía el cliente generado de OpenAPI (`src/lib`).
- Canvas: React Flow + ELK.js para auto-layout. La IA nunca pisa el layout manual (merge: nuevos
  auto-posicionados, existentes conservan posición).

## Governance de código

- Commits convencionales (`feat:`, `fix:`, `refactor:`). Una fase de la spec = un milestone.
- Cualquier desvío de la spec → ADR corto en `docs/adr/`.
- La IA (vía MCP) **no** aprueba, publica ni borra en cascada. Solo crea/edita drafts y solicita
  aprobación (SPEC §9).

## Estado de implementación

- **Fase 1 — Núcleo del repositorio + DSL** (backend completo, 22 tests verdes):
  - ✅ Registry (SSOT de tipos/relaciones, §4.2).
  - ✅ Motor DSL: parser, validator, importer (model/patch/replace), exporter, diff semántico.
  - ✅ Modelos SQLAlchemy (§6) + Alembic (migración inicial, up/down verificados) + mapeo
    repositorio ⇆ `ModelGraph` + multi-tenancy (`tenant_id` por dependencia).
  - ✅ API REST `/api/v1`: `meta/registry`, `dsl/import|export|schema`, catálogo
    (elements/relationships), views + versiones + diff. `audit_log` en cada mutación.
  - ✅ Auth: interfaz `AuthProvider` + stub de dev (seed tenant/admin). RBAC por rol.
  - ✅ Endpoints `impact` (BFS), `elements/{slug}/views` y `render` SVG server-side (coloreado por capa).
  - ✅ **Entra ID OIDC** (`EntraAuthProvider`): validación JWKS/RS256, issuer/audience/exp, mapeo de
    roles (app-roles + grupos) y provisioning JIT. Stub de dev sigue disponible. Tests con JWT auto-firmado.
  - ✅ **Jobs arq/Redis**: worker (`app/workers/main.py`) con snapshot diario del modelo + `enqueue`
    con **fallback inline** si no hay Redis. Correr: `arq app.workers.main.WorkerSettings`.
  - ✅ **RLS Postgres**: migración guardada a Postgres (políticas por tenant vía GUC `app.arqhub_tenant_id`,
    `core/tenancy.py`) — segunda línea sobre el filtrado explícito. Enforcement pleno (FORCE + rol
    dedicado) queda para hardening de Fase 6; no verificable sin Postgres.
- **Fase 2 — Canvas ArchiMate + catálogo** (funcional):
  - ✅ Frontend scaffolding (React 18 + TS + Vite + Tailwind + TanStack Query), build limpio.
  - ✅ App shell, Catálogo con filtros, Ficha de elemento (relaciones + navegación "aparece en"),
    Explorador de vistas con thumbnails SVG.
  - ✅ **Editor canvas React Flow** (`src/canvas/`): custom nodes ArchiMate (color por capa + ícono),
    custom edges por relación (línea/punta según [notación](docs/archimate-notation.md)), ELK
    auto-layout, paleta catálogo+nuevo, panel de propiedades, conectar→crear relación, persistencia
    de layout (`PUT /views/{slug}/layout`). Verificado E2E contra el backend.
  - ⏳ Pendiente Fase 2: drag & drop real desde la paleta, undo/redo, snap-to-grid, merge fino de
    layout manual vs auto al importar por IA.
- **Fase 3 — BPMN/UML + exportadores** (en curso):
  - ✅ **Exportadores estándar** (`services/exporters/`): ArchiMate Open Exchange XML, **BPMN 2.0 XML
    con BPMNDI** (abre en Camunda), XMI (UML). Endpoints `/export/{archimate,bpmn,xmi,image}`. Tests
    parsean y validan el XML.
  - ✅ Canvas consciente del lenguaje: nodos BPMN (task redondeada, evento círculo, gateway rombo) y
    UML (estereotipo), más menú **Exportar** en el editor.
  - ⏳ Pendiente Fase 3: pools/lanes BPMN como subflows (§16, prototipo), drill-down proceso→BPMN, PNG.
- Fases 4–6: governance+Teams, MCP+análisis, hardening (ver SPEC §14).

## Cómo correr el frontend

```bash
cd frontend && npm install          # requiere salida al registry npm (proxy corporativo)
cd frontend && npm run dev          # UI en :5173, proxy /api -> backend :8000
cd frontend && npm run build        # typecheck (tsc -b) + build de producción
```

## Cómo correr el backend

```bash
cd backend && ./.venv/Scripts/python.exe -m pytest -q          # tests
cd backend && ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload   # API en :8000, docs en /docs
```

Dev corre sobre SQLite sin infra. Para Postgres/Redis: `docker compose up` desde la raíz.

# Plataforma de Arquitectura Empresarial Model-First / IA-First

**Nombre de trabajo:** ArqHub (placeholder, renombrable)
**Versión del documento:** 1.0 — Julio 2026
**Propósito de este documento:** Especificación técnica completa para implementación con Claude Code. Contiene visión, alcance, metamodelo, DSL, arquitectura, modelo de datos, API, MCP, workflows de governance e integraciones. El componente SLM queda **fuera de alcance** en esta versión (previsto para una fase futura; se dejan los hooks arquitectónicos).

---

## 1. Visión y principios

Plataforma web para que **cualquier persona** (no solo arquitectos) cree, navegue, catalogue, versione y publique diagramas **ArchiMate, BPMN y UML**, con la IA como usuario de primera clase.

### Principios rectores (en orden de prioridad)

1. **Usabilidad**: onboarding sin fricción, canvas drag & drop completo, cero curva de aprendizaje para consumir diagramas.
2. **Diseño**: UI moderna, limpia, con identidad propia. No debe parecer una herramienta CASE de 2005.
3. **Integración con IA**: toda operación posible por UI debe ser posible por MCP. El formato de intercambio (DSL) está optimizado para ser generado y leído por LLMs.

### Decisión arquitectónica central: model-first

- El corazón NO son los diagramas: es un **repositorio semántico único** (metamodelo propio).
- Un elemento (ej. "API de Pagos") se define **una sola vez** y se proyecta como:
  - ArchiMate → `Application Component`
  - BPMN → `Participant` / `Lane`
  - UML → `Component`
- Los diagramas son **vistas** (`views`) del modelo. El catálogo de componentes ES el modelo.
- La navegación entre diagramas es automática: todo elemento sabe en qué vistas aparece.

### Separación semántica / presentación

- El **DSL no lleva coordenadas**. La IA genera semántica pura; el layout inicial lo calcula el motor (ELK.js).
- Cuando un humano acomoda elementos en el canvas, las posiciones se persisten en un objeto `layout` asociado a la vista (separado del modelo).
- La IA nunca pisa el layout manual. El humano nunca pierde su acomodo al regenerar una vista (merge: elementos nuevos se auto-layoutean, los existentes conservan posición).

---

## 2. Alcance

### Incluido (v1)

- Repositorio semántico con catálogo de elementos y relaciones.
- Editor canvas drag & drop para los tres lenguajes (ArchiMate 3.2, BPMN 2.0, UML 2.5 — subconjuntos definidos en §4).
- DSL propio en YAML: import/export, fuente de verdad para IA.
- Exportadores a formatos estándar: ArchiMate Open Exchange XML, BPMN 2.0 XML, XMI (UML). Export a PNG/SVG.
- Versionado de modelo y vistas con diff semántico.
- Estados y workflow de publicación: `draft → in_review → published → deprecated`.
- Solicitudes de aprobación reflejadas visualmente en el diagrama (badge de estado).
- Autenticación con **Microsoft Entra ID** (OIDC), roles y mapeo de grupos.
- Notificaciones a **Microsoft Teams** vía Graph API con Adaptive Cards (aprobar/rechazar desde Teams).
- **MCP server** con el set completo de tools (§9).
- Multi-tenancy por diseño (tenant_id en todo el modelo), aunque el despliegue inicial sea single-tenant on-prem.

### Excluido (v1)

- SLM propio (fine-tuning, inferencia local). Se deja el hook: la capa IA consume cualquier endpoint OpenAI-compatible configurable.
- Edición colaborativa en tiempo real (CRDT). v1: locking optimista por vista.
- Simulación/ejecución BPMN.
- Facturación / billing SaaS.
- Mobile app nativa (la web debe ser responsive para lectura/navegación).

---

## 3. Stack tecnológico

| Capa | Tecnología | Justificación |
|---|---|---|
| Frontend | React 18 + TypeScript + Vite | Estándar, tipado fuerte |
| Canvas | **React Flow** (@xyflow/react v12) | Custom nodes, edges, minimap, madurez |
| Layout automático | **ELK.js** (elkjs) | Layered layout, soporta puertos y jerarquías |
| Estado front | Zustand + TanStack Query | Simple, performante |
| UI kit | Tailwind CSS + shadcn/ui + lucide-react | Velocidad + estética moderna |
| Backend | **Python 3.12 + FastAPI** | Ecosistema IA, Pydantic para el DSL |
| ORM | SQLAlchemy 2 + Alembic | Migraciones versionadas |
| DB | **PostgreSQL 16** (JSONB para snapshots, tablas relacionales para el modelo vivo) | Un solo motor para todo |
| Cache/colas | Redis + arq (jobs async: exports, notificaciones) | Liviano |
| MCP server | Python SDK oficial de MCP (`mcp`), transporte HTTP streamable + stdio | Compatibilidad máxima |
| Auth | Entra ID OIDC (MSAL) detrás de una interfaz `AuthProvider` abstracta | No casarse con Azure de cara al SaaS |
| Notificaciones | Microsoft Graph API + Bot Framework (Adaptive Cards) | Aprobación desde Teams |
| Infra | Docker Compose (dev) / contenedores para AKS o Azure Container Apps (prod) | Mismo artefacto on-prem y cloud |
| Testing | pytest + Playwright (E2E del canvas) | |

---

## 4. Metamodelo

### 4.1 Entidades núcleo

```
Tenant ─┬─ Domain (dominio de negocio/arquitectura, mapeable a grupo AD)
        ├─ Element
        ├─ Relationship
        ├─ View
        ├─ ModelVersion (snapshot)
        ├─ ApprovalRequest
        └─ User / Role
```

**Element**
- `id` (slug estable legible, ej. `api-pagos` — clave para que los LLMs referencien sin UUIDs opacos; UUID interno aparte)
- `name`, `description`, `domain_id`, `owner` (user o equipo)
- `kind`: tipo canónico del catálogo (ver 4.2)
- `mappings`: tipo concreto en cada lenguaje (derivado de `kind` por defecto, sobreescribible)
- `lifecycle`: `proposed | active | deprecated | retired`
- `tags[]`, `properties{}` (key-value extensible)
- `tenant_id`, timestamps, auditoría

**Relationship**
- `id`, `from_element`, `to_element`
- `kind` canónico + mapeo por lenguaje (ej. canónico `uses` → ArchiMate `serving`, UML `dependency`, BPMN `message-flow`)
- `label`, `properties{}`

**View**
- `id` (slug), `name`, `lang`: `archimate | bpmn | uml`
- `viewpoint` (opcional, ej. `application-cooperation`)
- `include`: lista de element ids + relationship ids (o `auto: true` para incluir relaciones entre los elementos incluidos)
- `layout`: posiciones/tamaños por elemento (separado, ver §1)
- `status`: `draft | in_review | published | deprecated`
- `version` actual + historial

### 4.2 Tipos canónicos y mapeos (subconjuntos v1)

El catálogo trabaja con **kinds canónicos**; cada lenguaje tiene su proyección. Tabla de mapeo por defecto (extensible por config):

| Kind canónico | ArchiMate 3.2 | UML 2.5 | BPMN 2.0 |
|---|---|---|---|
| `actor` | Business Actor | Actor | Participant (pool) |
| `role` | Business Role | Actor | Lane |
| `process` | Business Process | Activity | Process / Sub-process |
| `task` | Business Process | Action | Task (user/service/script) |
| `event` | Business Event | Signal | Event (start/intermediate/end) |
| `gateway` | Junction | Decision node | Gateway (exclusive/parallel/inclusive) |
| `service` | Application/Business Service | Interface | — |
| `app-component` | Application Component | Component | Participant |
| `interface` | Application Interface | Interface | — |
| `data-object` | Data Object | Class | Data Object |
| `node` | Node (Technology) | Node | — |
| `artifact` | Artifact | Artifact | — |
| `capability` | Capability | — | — |
| `goal` | Goal (Motivation) | — | — |

Relaciones canónicas v1: `composition`, `aggregation`, `assignment`, `realization`, `serving` (`uses`), `access`, `triggering` (`flow`), `association`, `specialization`. BPMN además: `sequence-flow`, `message-flow`. Validación: matriz de relaciones permitidas por lenguaje (ArchiMate tiene reglas estrictas; implementar como tabla de validación, devolver warnings, no bloquear salvo violación dura).

Elementos exclusivos de un lenguaje (ej. un gateway BPMN puro) se guardan igual en el repositorio con `kind` específico y mapeo solo a su lenguaje.

---

## 5. DSL (formato de intercambio IA-first)

### 5.1 Diseño

- **YAML** estricto, validado con Pydantic (JSON Schema publicado en `/schema/dsl.json` para que las IAs lo consuman).
- Sin coordenadas, sin estilos obligatorios, ids legibles (slugs).
- Un archivo puede contener modelo completo, un delta, o una vista.
- Roundtrip garantizado: `export(import(x)) == x` (semánticamente).

### 5.2 Ejemplo canónico

```yaml
dsl: arqhub/1.0
model:
  elements:
    portal-web:
      name: Portal Web Clientes
      kind: app-component
      domain: canales
      owner: equipo-canales
      lifecycle: active
      tags: [frontend, publico]
    api-pagos:
      name: API de Pagos
      kind: app-component
      domain: integraciones
      description: Expone operaciones de pago a canales.
    originacion:
      name: Originación de Crédito
      kind: process
      domain: creditos
  relations:
    - id: r-portal-usa-pagos
      from: portal-web
      to: api-pagos
      kind: uses
      label: consulta y ejecuta pagos
    - id: r-orig-usa-pagos
      from: originacion
      to: api-pagos
      kind: uses
views:
  - id: vista-app-pagos
    name: Cooperación de Aplicaciones - Pagos
    lang: archimate
    viewpoint: application-cooperation
    include:
      elements: [portal-web, api-pagos]
      relations: auto        # incluye relaciones entre los elementos listados
  - id: proceso-originacion
    name: Proceso de Originación
    lang: bpmn
    include:
      elements: [originacion, api-pagos]
      relations: auto
```

### 5.3 Operaciones delta (para diálogo con IA)

```yaml
dsl: arqhub/1.0
patch:
  add_elements:
    motor-scoring: { name: Motor de Scoring, kind: app-component, domain: creditos }
  add_relations:
    - { from: originacion, to: motor-scoring, kind: uses }
  update_elements:
    api-pagos: { lifecycle: deprecated }
  remove_relations: [r-portal-usa-pagos]
```

El endpoint de import acepta `model` completo (merge o replace) o `patch`. Toda importación corre validación y devuelve reporte estructurado (errores, warnings, resumen del diff) — pensado para que un LLM pueda autocorregirse.

---

## 6. Modelo de datos (PostgreSQL)

Tablas principales (todas con `tenant_id`, `created_at`, `updated_at`, `created_by`):

```sql
tenants(id, name, slug, settings jsonb)
users(id, tenant_id, entra_oid, email, display_name, role)  -- role: viewer|editor|approver|admin
domains(id, tenant_id, slug, name, ad_group_id nullable)
elements(id uuid, tenant_id, slug, name, kind, domain_id, owner_id,
         description, lifecycle, tags text[], properties jsonb,
         mappings jsonb, deleted_at)
relationships(id uuid, tenant_id, slug, from_element, to_element,
              kind, label, properties jsonb, deleted_at)
views(id uuid, tenant_id, slug, name, lang, viewpoint,
      include jsonb, status, current_version int)
view_layouts(view_id, element_id, x, y, w, h, style jsonb)  -- presentación, fuera del modelo
model_versions(id, tenant_id, scope, scope_id nullable, version int,
               snapshot jsonb, message, author_id, created_at)
      -- scope: 'model' (snapshot global) | 'view'
approval_requests(id, tenant_id, view_id, view_version, requested_by,
                  status, approvers jsonb, resolved_by, resolved_at,
                  comment, teams_message_id)
      -- status: pending|approved|rejected|cancelled
audit_log(id, tenant_id, actor_id, actor_type, action, entity, entity_id,
          payload jsonb, at)
      -- actor_type: user|mcp|system  ← trazabilidad de qué hizo la IA
```

Notas:
- `slug` único por tenant y entidad; es el id que ve el DSL y la IA.
- Soft delete en elements/relationships (un elemento puede estar en vistas publicadas).
- Versionado: snapshot JSONB del DSL en `model_versions`; diff semántico calculado comparando snapshots (elementos/relaciones agregados, quitados, modificados). No diff de texto.

---

## 7. API REST (FastAPI, prefijo `/api/v1`)

Auth: Bearer JWT de Entra ID (validación de firma + audience). Para MCP y automatización: PAT/API keys por usuario con scopes.

```
# Catálogo
GET/POST        /elements                (filtros: kind, domain, lifecycle, tag, q)
GET/PATCH/DELETE /elements/{slug}
GET             /elements/{slug}/views        # navegación: dónde aparece
GET             /elements/{slug}/impact       # grafo de impacto (BFS sobre relaciones, profundidad param)
GET/POST        /relationships
GET/PATCH/DELETE /relationships/{slug}

# Vistas
GET/POST        /views
GET/PATCH/DELETE /views/{slug}
GET             /views/{slug}/render          # SVG server-side (para Teams cards y export)
PUT             /views/{slug}/layout          # persistir posiciones del canvas
POST            /views/{slug}/versions        # crear versión (commit) con message
GET             /views/{slug}/versions
GET             /views/{slug}/diff?from=&to=  # diff semántico estructurado

# DSL
GET             /dsl/export?scope=model|view&id=&lang=   # YAML
POST            /dsl/import                              # model|patch; ?dry_run=true
GET             /dsl/schema                              # JSON Schema del DSL

# Exportadores estándar
GET             /export/archimate?view=      # Open Exchange XML
GET             /export/bpmn?view=           # BPMN 2.0 XML (con BPMNDI desde layout)
GET             /export/xmi?view=            # XMI
GET             /export/image?view=&format=svg|png

# Governance
POST            /views/{slug}/submit-review    {approvers:[...], comment}
POST            /approvals/{id}/approve|reject {comment}
GET             /approvals?status=&mine=true
POST            /views/{slug}/publish          # requiere approval aprobada
POST            /views/{slug}/deprecate

# Admin
GET/POST        /domains ; PATCH /domains/{slug}   (mapeo grupo AD)
GET             /users/me
```

Todas las mutaciones escriben `audit_log` con `actor_type` correcto.

---

## 8. Frontend

### 8.1 Estructura de la app

- **Layout**: sidebar izquierda (navegación: Catálogo, Vistas, Aprobaciones, Admin) + topbar (búsqueda global ⌘K, usuario, tenant).
- **Catálogo**: tabla/cards de elementos con filtros por kind/dominio/estado/tag; ficha de elemento con sus propiedades, relaciones (mini-grafo) y lista de vistas donde aparece (click → abre la vista con el elemento resaltado y centrado).
- **Explorador de vistas**: grilla con thumbnail SVG, lang, estado (badge), versión, owner.
- **Editor canvas** (núcleo, ver 8.2).
- **Aprobaciones**: bandeja de pendientes propias y solicitadas.

### 8.2 Editor canvas (React Flow)

- **Paleta izquierda** con dos pestañas: *Catálogo* (buscar y arrastrar elementos existentes → reutilización primero) y *Nuevo* (stencils del lenguaje de la vista; al soltar, modal mínimo nombre+kind y se crea en el repositorio).
- **Custom nodes** por lenguaje con la notación visual correcta:
  - ArchiMate: rectángulos con ícono de tipo en esquina superior derecha, colores por capa (negocio amarillo, aplicación azul, tecnología verde, motivación violeta) — paleta ajustada al design system, no los colores crudos del estándar.
  - BPMN: tasks redondeadas con ícono de tipo, eventos circulares, gateways rombo, pools/lanes como grupos contenedores (React Flow subflows).
  - UML: componentes con estereotipo, clases con compartimentos, actores stickman.
- **Custom edges** por tipo de relación (flechas/puntas según notación de cada lenguaje).
- **Conexión**: drag desde handles; al conectar, selector de tipo de relación filtrado por la matriz de validación (§4.2). Relación inválida → no se ofrece; discutible → warning inline.
- **Auto-layout**: botón "Organizar" (ELK layered, dirección configurable). Al agregar elementos vía IA/import, solo los nuevos se auto-posicionan.
- **Panel derecho contextual**: propiedades del elemento/relación seleccionado (edita el repositorio, con aviso de que impacta otras vistas: "aparece en 4 vistas más").
- **Badge de estado** flotante en el canvas: `Borrador` / `En revisión (esperando a X)` / `Publicada v3` / `Deprecada`, con acceso al historial y al botón de submit/publish según rol.
- **Navegación entre diagramas**: click derecho en elemento → "Ver en otras vistas" (lista con lang y estado); doble click en elemento tipo `process` con vista BPMN asociada → drill-down.
- Undo/redo, snap to grid, minimap, zoom to fit, atajos de teclado.
- **Modo lectura** para vistas publicadas (perfil viewer): sin edición, navegación fluida, export.

### 8.3 Diseño visual

- Design system propio sobre Tailwind: tipografía Inter, esquema claro por defecto con dark mode, superficies con bordes sutiles, microinteracciones (hover states, transiciones 150ms).
- Los diagramas deben verse **bien por defecto**: espaciado generoso del auto-layout, tipografía legible en zoom out, edges con routing ortogonal para ArchiMate/UML y curvas suaves para BPMN.

---

## 9. MCP Server

Servicio separado (`arqhub-mcp`) que consume la API REST con credenciales del usuario (PAT) o service account con scopes. Transporte: HTTP streamable (remoto) y stdio (local para Claude Code). Toda acción vía MCP queda en `audit_log` como `actor_type='mcp'`.

### Tools

| Tool | Descripción |
|---|---|
| `search_catalog` | Busca elementos por texto/kind/domain/tag. Devuelve slugs + resumen. |
| `get_element` | Ficha completa: propiedades, relaciones, vistas donde aparece. |
| `query_model` | Preguntas estructurales: vecinos, caminos entre dos elementos, análisis de impacto (profundidad N). |
| `export_dsl` | Exporta modelo o vista en DSL YAML. |
| `import_dsl` | Aplica `model` o `patch`; soporta `dry_run` para validar antes de aplicar. Devuelve reporte de validación + diff. |
| `create_element` / `update_element` | Alta/modificación individual. |
| `create_relationship` | Alta con validación de matriz. |
| `generate_view` | Crea una vista dado lang + lista de elementos (o criterio: "todo el dominio X"), status draft, auto-layout. Devuelve URL. |
| `get_view` | Metadata + DSL de la vista + estado de aprobación. |
| `render_view` | Devuelve SVG de la vista (para que el LLM lo adjunte o el usuario lo vea). |
| `diff_versions` | Diff semántico entre versiones de una vista o del modelo. |
| `request_approval` | Somete una vista a revisión con lista de aprobadores. |
| `get_approval_status` | Estado de las solicitudes de una vista. |
| `propose_optimization` | Corre las reglas de análisis (§10) y devuelve hallazgos estructurados. |

### Reglas de seguridad MCP

- La IA **no puede** aprobar (`approve/reject` no se exponen como tools) ni publicar ni borrar en cascada. Puede crear, modificar drafts, y solicitar aprobación.
- Mutaciones sobre vistas `published` → rechazadas; debe crear nueva versión draft.
- Rate limiting por token.

---

## 10. Motor de análisis y optimización (sin SLM)

Reglas determinísticas sobre el grafo, expuestas en UI ("Analizar modelo") y vía MCP (`propose_optimization`):

- **Duplicados probables**: elementos del mismo kind con nombres similares (trigram similarity pg_trgm > umbral) o mismas relaciones.
- **Huérfanos**: elementos sin relaciones o que no aparecen en ninguna vista.
- **Inconsistencias de ciclo de vida**: elemento `deprecated` con relaciones entrantes desde elementos `active`; vista publicada que contiene elementos `retired`.
- **Violaciones de la matriz de relaciones** (warnings acumulados).
- **Acoplamiento**: elementos con fan-in/fan-out por encima de percentil configurable.
- **Vistas desactualizadas**: publicadas hace > N días con elementos modificados después de la publicación.

Salida estructurada (JSON) con severidad, explicación y acción sugerida — formato pensado para que un LLM la consuma vía MCP y proponga el patch correspondiente. Hook futuro: estos hallazgos + el DSL son el input natural del SLM cuando se retome.

---

## 11. Governance: versionado, publicación, aprobaciones

### Versionado

- Commit manual por vista ("Guardar versión" con mensaje) + auto-snapshot al someter a revisión y al publicar.
- Snapshot global del modelo: diario (job) + manual.
- Diff semántico visual: panel con tres secciones (agregado/quitado/modificado) + resaltado en canvas (verde/rojo/amarillo) comparando dos versiones.

### Workflow de aprobación

```
draft ──submit-review──► in_review ──approve──► (publicable) ──publish──► published
  ▲                         │ reject                                        │ deprecate
  └─────────────────────────┘                                               ▼
                                                                        deprecated
```

- Al someter: se congela snapshot de la versión, se crea `approval_request` con 1..N aprobadores (usuarios con rol `approver` o superior; configurable si requiere todos o uno).
- El badge en el canvas refleja el estado en tiempo real, incluyendo quiénes aprobaron y quién falta.
- Editar una vista `in_review` → cancela la solicitud (con confirmación) y vuelve a draft.
- `publish` requiere solicitud aprobada sobre la versión vigente.

### Notificaciones Teams

- **Bot registrado en Entra** (Bot Framework) + Graph API.
- Al someter a revisión: cada aprobador recibe **Adaptive Card** en chat personal con: nombre de vista, lang, solicitante, mensaje, **thumbnail SVG→PNG** de la vista, botones **Aprobar / Rechazar** (con campo comentario) y link a la plataforma. La acción del botón pega contra `/api/v1/approvals/{id}` con el token del flujo del bot.
- Al resolverse: notificación al solicitante; la card original se actualiza (refresh) mostrando el resultado.
- Eventos adicionales configurables por usuario: publicación de vistas de mi dominio, cambios en elementos que soy owner.
- Fallback: si el tenant no tiene Teams habilitado, email (SMTP configurable).

---

## 12. Seguridad y multi-tenancy

- **Entra ID OIDC**: login web (auth code + PKCE), tokens validados en API. Interfaz `AuthProvider` para poder sumar otros IdPs en la fase SaaS.
- Roles: `viewer` (lee publicado), `editor` (crea/edita drafts), `approver` (aprueba + editor), `admin` (todo + config).
- Mapeo opcional de **grupos AD → dominios**: pertenecer al grupo otorga rol editor en ese dominio (config por tenant).
- Permisos por dominio: un editor solo edita elementos/vistas de sus dominios (los admin, todo).
- `tenant_id` en todas las queries vía dependencia FastAPI (nunca confiar en el cliente). Row Level Security de Postgres como segunda línea.
- Secrets por variables de entorno / Key Vault. Sin secretos en el repo.
- Audit log inmutable (append-only) de toda mutación, humana o IA.

---

## 13. Estructura del repositorio

```
arqhub/
├── docker-compose.yml            # dev: db, redis, api, web, mcp
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                 # config, auth, deps, tenancy
│   │   ├── models/               # SQLAlchemy
│   │   ├── schemas/              # Pydantic (incluye DSL)
│   │   ├── api/v1/               # routers por recurso
│   │   ├── services/
│   │   │   ├── dsl/              # parser, validator, importer, exporter
│   │   │   ├── exporters/        # archimate_xml, bpmn_xml, xmi, svg
│   │   │   ├── versioning.py     # snapshots y diff semántico
│   │   │   ├── analysis.py       # reglas de optimización
│   │   │   ├── approvals.py
│   │   │   └── notifications/    # teams (graph), email
│   │   └── workers/              # arq jobs
│   ├── alembic/
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── app/                  # rutas
│   │   ├── features/             # catalog, views, editor, approvals, admin
│   │   ├── canvas/               # nodes/, edges/, layout/ (ELK), palette/
│   │   ├── components/ui/        # shadcn
│   │   └── lib/                  # api client (generado de OpenAPI), auth
│   └── e2e/                      # Playwright
├── mcp-server/
│   └── src/                      # tools, transportes, cliente API
├── docs/
│   ├── dsl-spec.md               # especificación formal del DSL + JSON Schema
│   └── adr/                      # decisiones de arquitectura
└── CLAUDE.md                     # convenciones para Claude Code
```

---

## 14. Plan de implementación por fases

Cada fase termina con criterios de aceptación verificables. Orden pensado para tener valor usable temprano.

### Fase 1 — Núcleo del repositorio + DSL (fundacional)
- Modelo de datos completo, migraciones, multi-tenancy, seed de tipos canónicos y matriz de relaciones.
- CRUD elementos/relaciones/vistas por API.
- DSL: parser/validator Pydantic, import (model/patch/dry_run), export, JSON Schema publicado.
- Versionado con snapshots y diff semántico (API).
- Auth Entra ID + roles (sin mapeo AD todavía).
- ✅ *Aceptación*: importar el YAML de ejemplo §5.2 por API, exportarlo idéntico, ver diff entre dos imports.

### Fase 2 — Canvas ArchiMate + catálogo (primera UI usable)
- App shell, catálogo con fichas y navegación elemento→vistas.
- Editor React Flow con nodes/edges ArchiMate, paleta catálogo+nuevo, ELK auto-layout, persistencia de layout, panel de propiedades, undo/redo.
- Render SVG server-side + export imagen.
- ✅ *Aceptación*: crear desde cero una vista ArchiMate de 15 elementos vía UI, importar un patch DSL que agrega 3 elementos y verificar que el layout manual no se pierde.

### Fase 3 — BPMN + UML
- Nodes/edges BPMN (pools/lanes como subflows, gateways, eventos) y UML (subset §4.2).
- Exportadores BPMN 2.0 XML (con BPMNDI), ArchiMate Open Exchange, XMI.
- Drill-down proceso→BPMN y "ver en otras vistas".
- ✅ *Aceptación*: el mismo elemento `api-pagos` visible y navegable en una vista de cada lenguaje; BPMN exportado abre en Camunda Modeler.

### Fase 4 — Governance + Teams
- Workflow completo draft→review→publish con badge en canvas y diff visual entre versiones.
- Bot Teams + Adaptive Cards con aprobación desde Teams y refresh de card.
- Mapeo grupos AD→dominios, permisos por dominio.
- Bandeja de aprobaciones en UI. Fallback email.
- ✅ *Aceptación*: flujo E2E: editor somete, approver aprueba desde Teams, badge cambia, publish habilitado.

### Fase 5 — MCP + análisis
- MCP server con el set completo de tools §9, transportes HTTP y stdio, PATs con scopes.
- Motor de análisis §10 en UI y MCP.
- Documentación del DSL para consumo de LLMs (`docs/dsl-spec.md` con ejemplos few-shot).
- ✅ *Aceptación*: desde Claude Code conectado por MCP: buscar elementos, generar una vista draft nueva, correr `propose_optimization`, aplicar un patch sugerido y someter a aprobación. Todo trazado en audit_log como `mcp`.

### Fase 6 — Pulido y hardening
- Dark mode, atajos, performance canvas (>200 nodos fluido), modo lectura optimizado.
- RLS Postgres, rate limiting, pentest básico, backup/restore.
- Empaquetado: compose productivo on-prem + manifests AKS/Container Apps.

---

## 15. Convenciones para Claude Code (volcar a CLAUDE.md del repo)

- Idioma del código e identificadores: **inglés**. UI y documentación de usuario: **español**.
- Backend: type hints obligatorios, Pydantic para todo I/O, servicios sin lógica en routers, tests pytest por servicio (mínimo happy path + 2 edge cases).
- Frontend: componentes funcionales, sin `any`, estado global solo en Zustand stores por feature, llamadas API solo vía cliente generado de OpenAPI.
- Todo cambio de modelo de datos → migración Alembic con downgrade funcional.
- La matriz de tipos/relaciones (§4.2) vive en `backend/app/services/dsl/registry.py` como única fuente de verdad; front la consume por endpoint `/api/v1/meta/registry`.
- ADR corto en `docs/adr/` para cualquier desvío de esta spec.
- Commits convencionales (`feat:`, `fix:`, `refactor:`); una fase = un milestone.

---

## 16. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Sync bidireccional canvas↔modelo (el mayor costo de front) | Alto | Fase 2 dedicada solo a ArchiMate para estabilizar el patrón antes de replicar a BPMN/UML |
| BPMN con pools/lanes en React Flow (subflows anidados) | Medio | Prototipo spike al inicio de Fase 3; limitar anidamiento a 2 niveles en v1 |
| Fidelidad de exportadores estándar (Open Exchange/XMI son quisquillosos) | Medio | Validar contra Archi y Camunda Modeler como criterio de aceptación |
| Adaptive Cards con acciones requiere bot registrado y permisos de tenant M365 | Medio | Fallback email desde el día 1; documentar el registro del bot paso a paso |
| Scope creep de notaciones (ArchiMate/UML completos son enormes) | Alto | Subconjuntos cerrados de §4.2 en v1; extensión solo vía registry |

---

## 17. Fuera de alcance pero con hook previsto

- **SLM especializado**: la capa de análisis (§10) y el DSL ya generan el dataset natural (pares hallazgo→patch, instrucción→DSL). Cuando se retome: endpoint OpenAI-compatible configurable en `settings`, consumido por un servicio `ai_assist` que hoy no se implementa.
- Colaboración en tiempo real (CRDT/Yjs sobre el layout).
- Marketplace de viewpoints/plantillas por industria (fase SaaS).

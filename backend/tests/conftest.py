"""Shared fixtures: the canonical DSL example (SPEC §5.2) and the patch (§5.3)."""

import pytest

# Verbatim from SPEC §5.2 — the acceptance fixture for Phase 1.
EXAMPLE_DSL = """
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
      name: Originacion de Credito
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
    name: Cooperacion de Aplicaciones - Pagos
    lang: archimate
    viewpoint: application-cooperation
    include:
      elements: [portal-web, api-pagos]
      relations: auto
  - id: proceso-originacion
    name: Proceso de Originacion
    lang: bpmn
    include:
      elements: [originacion, api-pagos]
      relations: auto
"""

# Verbatim from SPEC §5.3.
PATCH_DSL = """
dsl: arqhub/1.0
patch:
  add_elements:
    motor-scoring: { name: Motor de Scoring, kind: app-component, domain: creditos }
  add_relations:
    - { from: originacion, to: motor-scoring, kind: uses }
  update_elements:
    api-pagos: { lifecycle: deprecated }
  remove_relations: [r-portal-usa-pagos]
"""


@pytest.fixture
def example_dsl() -> str:
    return EXAMPLE_DSL


@pytest.fixture
def patch_dsl() -> str:
    return PATCH_DSL

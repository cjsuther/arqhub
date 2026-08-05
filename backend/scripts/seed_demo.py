"""Seed de datos de demostración para ArqHub.

Puebla el tenant de dev con un escenario coherente ("Onboarding de Clientes")
para poder probar cada funcionalidad: catálogo por capas, vistas ArchiMate/BPMN
(con pools)/UML con layout, carpetas jerárquicas, buscador/agrupación y el flujo
de gobierno (una vista queda en revisión).

Uso (con el backend corriendo en :8000):

    ./.venv/Scripts/python.exe scripts/seed_demo.py
"""

from __future__ import annotations

import os
import sys

import httpx
import yaml

# Override with ARQHUB_SEED_BASE_URL to seed a remote/Docker stack
# (e.g. http://api:8000/api/v1 from within docker compose).
BASE = os.environ.get("ARQHUB_SEED_BASE_URL", "http://127.0.0.1:8000/api/v1")

# --- Modelo: elementos (clave = slug) --------------------------------------
ELEMENTS: dict[str, dict] = {
    # Negocio
    "cliente": {"name": "Cliente", "kind": "actor",
                "description": "Persona que solicita el alta como cliente."},
    "oficial-cuentas": {"name": "Oficial de Cuentas", "kind": "role",
                        "description": "Responsable de gestionar el alta."},
    "onboarding": {"name": "Onboarding de Clientes", "kind": "process",
                   "description": "Proceso de alta de un nuevo cliente."},
    "validar-identidad": {"name": "Validar Identidad", "kind": "task"},
    "evaluar-riesgo": {"name": "Evaluar Riesgo", "kind": "task"},
    "aprobar-alta": {"name": "Aprobar Alta", "kind": "task"},
    "solicitud-recibida": {"name": "Solicitud Recibida", "kind": "event"},
    "decision-riesgo": {"name": "¿Riesgo Aceptable?", "kind": "gateway"},
    # Aplicación
    "portal-web": {"name": "Portal Web", "kind": "app-component",
                   "description": "Canal por el que el cliente inicia el alta."},
    "core-clientes": {"name": "Core de Clientes", "kind": "app-component"},
    "kyc-service": {"name": "Servicio KYC", "kind": "service",
                    "description": "Know Your Customer: valida identidad y antecedentes."},
    "legajo-cliente": {"name": "Legajo de Cliente", "kind": "data-object"},
    # Tecnología
    "srv-app": {"name": "Servidor de Aplicaciones", "kind": "node"},
    # Motivación
    "reducir-fraude": {"name": "Reducir Fraude", "kind": "goal",
                       "description": "Objetivo estratégico que motiva el proceso."},
}

# --- Modelo: relaciones ----------------------------------------------------
def rel(frm: str, to: str, kind: str) -> dict:
    return {"from": frm, "to": to, "kind": kind}

RELATIONS: list[dict] = [
    rel("oficial-cuentas", "onboarding", "assignment"),
    rel("onboarding", "validar-identidad", "composition"),
    rel("onboarding", "evaluar-riesgo", "composition"),
    rel("onboarding", "aprobar-alta", "composition"),
    rel("solicitud-recibida", "validar-identidad", "triggering"),
    rel("validar-identidad", "evaluar-riesgo", "triggering"),
    rel("evaluar-riesgo", "decision-riesgo", "triggering"),
    rel("decision-riesgo", "aprobar-alta", "triggering"),
    rel("portal-web", "onboarding", "serving"),
    rel("kyc-service", "validar-identidad", "serving"),
    rel("core-clientes", "kyc-service", "realization"),
    rel("aprobar-alta", "legajo-cliente", "access"),
    rel("srv-app", "core-clientes", "assignment"),
    rel("onboarding", "reducir-fraude", "realization"),
    rel("portal-web", "core-clientes", "association"),
    rel("core-clientes", "legajo-cliente", "access"),
    # Membresía de pools BPMN (pool --assignment--> miembro)
    rel("cliente", "solicitud-recibida", "assignment"),
    rel("portal-web", "validar-identidad", "assignment"),
    rel("portal-web", "evaluar-riesgo", "assignment"),
    rel("portal-web", "decision-riesgo", "assignment"),
    rel("portal-web", "aprobar-alta", "assignment"),
]

# --- Vistas ----------------------------------------------------------------
VIEWS: list[dict] = [
    {
        "id": "onboarding-arquitectura", "name": "Onboarding — Arquitectura", "lang": "archimate",
        "viewpoint": "Layered",
        "include": {"elements": [
            "reducir-fraude", "cliente", "oficial-cuentas", "onboarding",
            "portal-web", "kyc-service", "core-clientes", "legajo-cliente", "srv-app",
        ], "relations": "auto"},
    },
    {
        "id": "onboarding-bpmn", "name": "Onboarding — Proceso (BPMN)", "lang": "bpmn",
        "include": {"elements": [
            "cliente", "portal-web", "solicitud-recibida",
            "validar-identidad", "evaluar-riesgo", "decision-riesgo", "aprobar-alta",
        ], "relations": "auto"},
    },
    {
        "id": "onboarding-componentes", "name": "Onboarding — Componentes (UML)", "lang": "uml",
        "include": {"elements": [
            "portal-web", "core-clientes", "kyc-service", "legajo-cliente",
        ], "relations": "auto"},
    },
]

# --- Layouts (presentación) ------------------------------------------------
def node(el: str, x: int, y: int, w: int = 170, h: int = 64, parent: str | None = None) -> dict:
    return {"element": el, "x": x, "y": y, "w": w, "h": h, "parent": parent, "style": {}}

LAYOUTS: dict[str, list[dict]] = {
    "onboarding-arquitectura": [
        node("reducir-fraude", 300, 20),
        node("cliente", 40, 130), node("oficial-cuentas", 260, 130), node("onboarding", 480, 130),
        node("portal-web", 40, 250), node("kyc-service", 260, 250),
        node("core-clientes", 480, 250), node("legajo-cliente", 700, 250),
        node("srv-app", 480, 370),
    ],
    "onboarding-bpmn": [
        node("cliente", 0, 0, 940, 120),
        node("solicitud-recibida", 70, 32, 150, 56, parent="cliente"),
        node("portal-web", 0, 150, 940, 140),
        node("validar-identidad", 70, 42, 150, 56, parent="portal-web"),
        node("evaluar-riesgo", 280, 42, 150, 56, parent="portal-web"),
        node("decision-riesgo", 490, 42, 150, 56, parent="portal-web"),
        node("aprobar-alta", 700, 42, 150, 56, parent="portal-web"),
    ],
    "onboarding-componentes": [
        node("portal-web", 40, 40), node("core-clientes", 320, 40),
        node("kyc-service", 320, 200), node("legajo-cliente", 600, 40),
    ],
}

# --- Carpetas: (nombre, scope, padre-por-nombre, items) --------------------
FOLDERS: list[dict] = [
    {"name": "Negocio", "scope": "element", "parent": None,
     "items": ["cliente", "oficial-cuentas", "onboarding", "solicitud-recibida", "decision-riesgo"]},
    {"name": "Tareas", "scope": "element", "parent": "Negocio",
     "items": ["validar-identidad", "evaluar-riesgo", "aprobar-alta"]},
    {"name": "Aplicaciones", "scope": "element", "parent": None,
     "items": ["portal-web", "core-clientes", "kyc-service", "legajo-cliente"]},
    {"name": "Tecnología", "scope": "element", "parent": None, "items": ["srv-app"]},
    {"name": "Motivación", "scope": "element", "parent": None, "items": ["reducir-fraude"]},
    {"name": "Onboarding", "scope": "view", "parent": None,
     "items": ["onboarding-arquitectura", "onboarding-bpmn", "onboarding-componentes"]},
]


def main() -> int:
    c = httpx.Client(base_url=BASE, timeout=30.0)

    # 1) Importar modelo + vistas por DSL
    doc = {"dsl": "arqhub/1.0",
           "model": {"elements": ELEMENTS, "relations": RELATIONS},
           "views": VIEWS}
    r = c.post("/dsl/import", content=yaml.safe_dump(doc, allow_unicode=True),
               headers={"Content-Type": "text/plain"})
    r.raise_for_status()
    report = r.json()
    if not report.get("applied"):
        print("ERROR: el import no se aplicó:", report.get("validation"))
        return 1
    diff = report.get("diff", {})
    print(f"Modelo importado. added elements={len(diff.get('added_elements', []))} "
          f"relations={len(diff.get('added_relations', []))} views={len(VIEWS)}")

    # 2) Layouts
    for slug, nodes in LAYOUTS.items():
        c.put(f"/views/{slug}/layout", json={"nodes": nodes}).raise_for_status()
    print(f"Layouts guardados para {len(LAYOUTS)} vistas.")

    # 3) Carpetas + asignación de items
    by_name: dict[tuple[str, str], str] = {}
    for f in FOLDERS:
        parent_id = by_name.get((f["parent"], f["scope"])) if f["parent"] else None
        resp = c.post("/folders", json={"name": f["name"], "scope": f["scope"],
                                        "parent_id": parent_id})
        resp.raise_for_status()
        fid = resp.json()["id"]
        by_name[(f["name"], f["scope"])] = fid
        path = "/elements" if f["scope"] == "element" else "/views"
        for slug in f["items"]:
            c.patch(f"{path}/{slug}/folder", json={"folder_id": fid}).raise_for_status()
    print(f"Carpetas creadas: {len(FOLDERS)} (con jerarquía Negocio → Tareas).")

    # 3b) Grupos + visibilidad de carpeta (demo de autorización)
    users_by_email = {u["email"]: u["id"] for u in c.get("/users").json()}
    g_arq = c.post("/groups", json={"name": "Arquitectura"}).json()
    c.post("/groups", json={"name": "Negocio TI"})
    if "caro@arqhub.local" in users_by_email:
        c.put(f"/users/{users_by_email['caro@arqhub.local']}/groups", json={"ids": [g_arq["id"]]})
    apps_folder = by_name.get(("Aplicaciones", "element"))
    if apps_folder:
        c.put(f"/folders/{apps_folder}/groups", json={"ids": [g_arq["id"]]})
    print("Grupos de ejemplo: 'Arquitectura' (Caro es miembro) puede ver la carpeta Aplicaciones.")

    # 4) Gobierno: dejar una vista en revisión para poblar la bandeja
    approvers = [u["id"] for u in c.get("/users", params={"role": "approver"}).json()]
    if approvers:
        rv = c.post("/views/onboarding-componentes/submit-review",
                    json={"approvers": approvers,
                          "comment": "Revisión inicial del diagrama de componentes."})
        if rv.status_code < 300:
            print("Vista 'Onboarding — Componentes (UML)' enviada a revisión.")
        else:
            print("Aviso: no se pudo enviar a revisión:", rv.status_code, rv.text)

    # 5) Historial de versiones en la vista de arquitectura, para demostrar la
    #    comparación de versiones (v1 → cambio → v2).
    c.post("/views/onboarding-arquitectura/versions", json={"message": "Versión inicial"})
    c.patch("/elements/onboarding",
            json={"description": "Proceso de alta de un nuevo cliente (revisado: incluye KYC)."})
    c.post("/views/onboarding-arquitectura/versions",
           json={"message": "Descripción del proceso ampliada"})
    print("Historial de versiones creado en 'Onboarding — Arquitectura' (v1 y v2).")

    # 6) Un comentario de ejemplo y documentación en una vista.
    c.post("/views/onboarding-bpmn/comments",
           json={"body": "¿El gateway de riesgo debería tener una rama de rechazo explícita?"})
    c.patch("/views/onboarding-bpmn", json={"notes": (
        "<h3>Proceso de Onboarding</h3><p>Flujo <strong>BPMN</strong> del alta de clientes. "
        "El pool <em>Portal Web</em> ejecuta las tareas; el <em>Cliente</em> inicia la solicitud.</p>"
        "<ul><li>KYC valida identidad</li><li>Riesgo evalúa el legajo</li></ul>")})
    print("Comentario y documentación de ejemplo agregados a 'Onboarding — Proceso (BPMN)'.")

    # 7) Ciclo de gobierno completo sobre la vista de arquitectura para demostrar
    #    la fecha/autor del estado: enviar → aprobar (con comentario) → publicar.
    me = c.get("/users/me").json()
    c.post("/views/onboarding-arquitectura/submit-review",
           json={"approvers": [me["id"]], "comment": "Lista para revisión de arquitectura."})
    ar = c.get("/approvals", params={"status": "pending"}).json()
    target = next((x for x in ar if x["view_slug"] == "onboarding-arquitectura"), None)
    if target:
        c.post(f"/approvals/{target['id']}/approve",
               json={"comment": "Aprobado: coherente con el objetivo de reducir fraude."})
        pub = c.post("/views/onboarding-arquitectura/publish")
        if pub.status_code < 300:
            print("'Onboarding — Arquitectura' publicada (con fecha, autor y decisión de aprobación).")

    print("\nSeed completo. Recargá la app para ver el catálogo, las vistas y las carpetas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

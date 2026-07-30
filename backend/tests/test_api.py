"""End-to-end API tests over HTTP (SPEC §7). Uses a throwaway SQLite file.

Env is set before importing the app so ``Settings`` picks up the temp DB.
"""

import os
import tempfile

_TMP_DB = os.path.join(tempfile.mkdtemp(), "arqhub_test.db")
os.environ["ARQHUB_DATABASE_URL"] = f"sqlite+pysqlite:///{_TMP_DB}"
os.environ["ARQHUB_DEV_AUTH"] = "true"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import EXAMPLE_DSL, PATCH_DSL

TEXT = {"Content-Type": "text/plain"}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_registry_endpoint(client):
    body = client.get("/api/v1/meta/registry").json()
    assert "app-component" in body["kinds"]
    assert body["relation_aliases"]["uses"] == "serving"


def test_dsl_schema_endpoint(client):
    schema = client.get("/api/v1/dsl/schema").json()
    assert schema["title"] == "DslDocument"


def test_import_then_roundtrip_export(client):
    r = client.post("/api/v1/dsl/import", content=EXAMPLE_DSL, headers=TEXT)
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["applied"] is True
    assert set(report["diff"]["elements"]["added"]) == {"portal-web", "api-pagos", "originacion"}

    exported = client.get("/api/v1/dsl/export").text
    # Re-importing the export must be a no-op (semantic roundtrip over HTTP).
    r2 = client.post("/api/v1/dsl/import?dry_run=true", content=exported, headers=TEXT)
    diff = r2.json()["diff"]
    assert diff["elements"]["added"] == [] and diff["elements"]["removed"] == []
    assert diff["relations"]["added"] == [] and diff["relations"]["removed"] == []


def test_catalog_reflects_import(client):
    els = client.get("/api/v1/elements").json()
    slugs = {e["slug"] for e in els}
    assert {"portal-web", "api-pagos", "originacion"} <= slugs

    one = client.get("/api/v1/elements/api-pagos").json()
    assert one["kind"] == "app-component"
    assert one["domain"] == "integraciones"


def test_relationship_alias_normalized_over_http(client):
    rels = client.get("/api/v1/relationships").json()
    by_id = {r["slug"]: r for r in rels}
    assert by_id["r-portal-usa-pagos"]["kind"] == "serving"
    assert by_id["r-portal-usa-pagos"]["from"] == "portal-web"


def test_create_and_update_element(client):
    payload = {"slug": "motor-scoring", "name": "Motor de Scoring", "kind": "app-component", "domain": "creditos"}
    r = client.post("/api/v1/elements", json=payload)
    assert r.status_code == 201, r.text

    r = client.patch("/api/v1/elements/motor-scoring", json={"lifecycle": "deprecated"})
    assert r.json()["lifecycle"] == "deprecated"

    # Duplicate slug -> 409.
    assert client.post("/api/v1/elements", json=payload).status_code == 409


def test_unknown_kind_is_422(client):
    r = client.post("/api/v1/elements", json={"slug": "x", "name": "X", "kind": "not-a-kind"})
    assert r.status_code == 422


def test_element_views_endpoint(client):
    body = client.get("/api/v1/elements/api-pagos/views").json()
    view_slugs = {v["slug"] for v in body}
    assert {"vista-app-pagos", "proceso-originacion"} <= view_slugs


def test_element_impact_bfs(client):
    body = client.get("/api/v1/elements/api-pagos/impact?depth=1&directed=false").json()
    slugs = {n["slug"] for n in body["nodes"]}
    assert {"api-pagos", "portal-web", "originacion"} <= slugs
    assert body["nodes"][0]["slug"] == "api-pagos"  # root at depth 0


def test_render_view_svg(client):
    r = client.get("/api/v1/views/vista-app-pagos/render")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/svg+xml")
    assert "<svg" in r.text and "API de Pagos" in r.text


def test_view_graph_and_layout_roundtrip(client):
    g = client.get("/api/v1/views/vista-app-pagos/graph").json()
    assert g["view"]["slug"] == "vista-app-pagos"
    slugs = {e["slug"] for e in g["elements"]}
    assert {"portal-web", "api-pagos"} <= slugs
    assert g["layout"] == []  # nothing persisted yet

    body = {"nodes": [
        {"element": "portal-web", "x": 10, "y": 20, "w": 170, "h": 64},
        {"element": "api-pagos", "x": 300, "y": 20, "w": 170, "h": 64},
    ]}
    assert client.put("/api/v1/views/vista-app-pagos/layout", json=body).status_code == 204

    g2 = client.get("/api/v1/views/vista-app-pagos/graph").json()
    layout = {n["element"]: n for n in g2["layout"]}
    assert layout["api-pagos"]["x"] == 300
    # PUT replaces the full set for the view.
    assert len(g2["layout"]) == 2


def test_view_versioning_and_diff(client):
    # Two versions of the same view with a change in between -> semantic diff.
    v1 = client.post("/api/v1/views/vista-app-pagos/versions", json={"message": "v1"}).json()
    assert v1["version"] == 1

    client.patch("/api/v1/elements/portal-web", json={"description": "canal digital"})
    v2 = client.post("/api/v1/views/vista-app-pagos/versions", json={"message": "v2"}).json()
    assert v2["version"] == 2

    diff = client.get("/api/v1/views/vista-app-pagos/diff?from=1&to=2").json()
    modified = {m["id"] for m in diff["elements"]["modified"]}
    assert "portal-web" in modified

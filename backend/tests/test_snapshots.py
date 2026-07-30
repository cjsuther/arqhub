"""Model snapshots (SPEC §11) and the enqueue-with-inline-fallback helper."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Base, Tenant
from app.services import jobs
from app.services.dsl import apply_document, load_dsl
from app.services.repository import sync_graph
from app.services.snapshots import create_model_snapshot
from tests.conftest import EXAMPLE_DSL


@pytest.fixture
def seeded():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    tenant = Tenant(slug="t", name="T", settings={})
    db.add(tenant)
    db.flush()
    graph = apply_document(None, load_dsl(EXAMPLE_DSL)).graph
    sync_graph(db, tenant.id, graph)
    db.commit()
    yield db, tenant.id
    db.close()


def test_snapshot_captures_model(seeded):
    db, tenant_id = seeded
    snap = create_model_snapshot(db, tenant_id, message="first")
    assert snap.version == 1
    assert snap.scope == "model"
    assert "portal-web" in snap.snapshot["model"]["elements"]


def test_snapshot_versions_increment(seeded):
    db, tenant_id = seeded
    create_model_snapshot(db, tenant_id)
    second = create_model_snapshot(db, tenant_id)
    assert second.version == 2


def test_enqueue_falls_back_to_inline(monkeypatch):
    calls: list[str] = []

    async def _fail(*_args):
        raise RuntimeError("no redis")

    monkeypatch.setattr(jobs, "_enqueue", _fail)
    monkeypatch.setattr(jobs, "run_snapshot", lambda t: calls.append(t) or "v1")

    assert jobs.enqueue_snapshot("tenant-x") == "inline"
    assert calls == ["tenant-x"]

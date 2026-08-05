"""Governance: multi-approver decisions, mandatory comment, status audit (SPEC §11)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import Principal
from app.models import Base, Tenant, User
from app.services import approvals, model_io
from app.services import views as views_svc

SEED = """
dsl: arqhub/1.0
model:
  elements:
    a: { name: A, kind: process }
views:
  - id: v1
    name: Vista 1
    lang: archimate
    include: { elements: [a], relations: auto }
"""


@pytest.fixture
def ctx():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    tenant = Tenant(slug="t", name="T", settings={})
    db.add(tenant)
    db.flush()
    admin = User(tenant_id=tenant.id, email="admin@x", display_name="Admin", role="admin")
    u1 = User(tenant_id=tenant.id, email="u1@x", display_name="Uno", role="approver")
    u2 = User(tenant_id=tenant.id, email="u2@x", display_name="Dos", role="approver")
    db.add_all([admin, u1, u2])
    db.flush()
    p = Principal(user_id=admin.id, tenant_id=tenant.id, email=admin.email, role="admin")
    model_io.import_dsl(db, p, SEED, dry_run=False, replace=False)
    yield db, tenant, p, admin, u1, u2
    db.close()


def _pr(tenant, u, role="approver"):
    return Principal(user_id=u.id, tenant_id=tenant.id, email=u.email, role=role)


def test_comment_is_mandatory(ctx):
    db, tenant, p, admin, u1, u2 = ctx
    ar = approvals.submit_review(db, p, "v1", [u1.id], None)
    with pytest.raises(Exception):
        approvals.approve(db, _pr(tenant, u1), ar.id, "")  # empty comment rejected


def test_multi_approver_requires_all(ctx):
    db, tenant, p, admin, u1, u2 = ctx
    ar = approvals.submit_review(db, p, "v1", [u1.id, u2.id], "revisen")
    # First approval → still pending.
    r1 = approvals.approve(db, _pr(tenant, u1), ar.id, "ok de mi lado")
    assert r1.status == "pending"
    assert len(r1.decisions) == 1 and r1.decisions[0].approver_name == "Uno"
    # Second approval → approved, with both decisions recorded.
    r2 = approvals.approve(db, _pr(tenant, u2), ar.id, "de acuerdo")
    assert r2.status == "approved"
    assert {d.approver_name for d in r2.decisions} == {"Uno", "Dos"}


def test_reject_sends_view_to_draft_with_author(ctx):
    db, tenant, p, admin, u1, u2 = ctx
    ar = approvals.submit_review(db, p, "v1", [u1.id, u2.id], "revisen")
    approvals.reject(db, _pr(tenant, u1), ar.id, "falta detalle")
    v = views_svc.get_view(db, tenant.id, "v1")
    assert v.status == "draft"
    assert v.status_changed_by == u1.id and v.status_changed_by_name == "Uno"
    assert v.status_changed_at is not None


def test_publish_records_status_author_and_date(ctx):
    db, tenant, p, admin, u1, u2 = ctx
    ar = approvals.submit_review(db, p, "v1", [u1.id], "revisá")
    approvals.approve(db, _pr(tenant, u1), ar.id, "aprobado")
    approvals.publish(db, _pr(tenant, admin, "admin"), "v1")
    v = views_svc.get_view(db, tenant.id, "v1")
    assert v.status == "published"
    assert v.status_changed_by_name == "Admin" and v.status_changed_at is not None

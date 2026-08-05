"""Collaboration features (SPEC §11): comments, connector rename, view notes,
version comparison."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import Principal
from app.models import Base, Tenant, User
from app.schemas.api import ElementUpdate, RelationshipUpdate, ViewUpdate
from app.services import approvals, catalog, model_io
from app.services import comments as comments_svc
from app.services import views as views_svc

SEED = """
dsl: arqhub/1.0
model:
  elements:
    a: { name: A, kind: process }
    b: { name: B, kind: app-component }
  relations:
    - id: r-ab
      from: b
      to: a
      kind: serving
      label: sirve
views:
  - id: v1
    name: Vista 1
    lang: archimate
    include:
      elements: [a, b]
      relations: auto
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
    other = User(tenant_id=tenant.id, email="ana@x", display_name="Ana", role="editor")
    db.add_all([admin, other])
    db.flush()
    p = Principal(user_id=admin.id, tenant_id=tenant.id, email=admin.email, role="admin")
    model_io.import_dsl(db, p, SEED, dry_run=False, replace=False)
    yield db, p, admin, other
    db.close()


# --- Connector rename --------------------------------------------------------
def test_rename_relationship(ctx):
    db, p, *_ = ctx
    r = catalog.update_relationship(db, p, "r-ab", RelationshipUpdate(label="nuevo nombre"))
    assert r.label == "nuevo nombre"


def test_rename_unknown_relationship_404(ctx):
    db, p, *_ = ctx
    with pytest.raises(Exception):
        catalog.update_relationship(db, p, "nope", RelationshipUpdate(label="x"))


# --- View notes (rich text) --------------------------------------------------
def test_view_notes_saved(ctx):
    db, p, *_ = ctx
    v = views_svc.update_view(db, p, "v1", ViewUpdate(notes="<p>hola</p>"))
    assert v.notes == "<p>hola</p>"


def test_notes_edit_keeps_review_but_name_cancels(ctx):
    db, p, admin, other = ctx
    approvals.submit_review(db, p, "v1", [other.id], None)
    assert views_svc.get_view(db, p.tenant_id, "v1").status == "in_review"
    # Editing only documentation must NOT cancel the review.
    views_svc.update_view(db, p, "v1", ViewUpdate(notes="<p>doc</p>"))
    assert views_svc.get_view(db, p.tenant_id, "v1").status == "in_review"
    # Editing a model-affecting field (name) cancels it back to draft.
    views_svc.update_view(db, p, "v1", ViewUpdate(name="Renombrada"))
    assert views_svc.get_view(db, p.tenant_id, "v1").status == "draft"


# --- Comments ----------------------------------------------------------------
def test_comments_crud_and_permissions(ctx):
    db, p, admin, other = ctx
    c = comments_svc.create_comment(db, p, "v1", "hola")
    assert c.body == "hola" and c.author_name == "Admin"
    assert len(comments_svc.list_comments(db, p.tenant_id, "v1")) == 1

    # Empty body is rejected.
    with pytest.raises(Exception):
        comments_svc.create_comment(db, p, "v1", "   ")

    # A different non-admin user cannot delete someone else's comment.
    p_other = Principal(user_id=other.id, tenant_id=p.tenant_id, email=other.email, role="editor")
    with pytest.raises(Exception):
        comments_svc.delete_comment(db, p_other, c.id)

    # The author can.
    comments_svc.delete_comment(db, p, c.id)
    assert len(comments_svc.list_comments(db, p.tenant_id, "v1")) == 0


# --- Version comparison ------------------------------------------------------
def test_version_diff_reports_field_change(ctx):
    db, p, *_ = ctx
    views_svc.create_view_version(db, p, "v1", "inicial")
    catalog.update_element(db, p, "a", ElementUpdate(description="cambiada"))
    views_svc.create_view_version(db, p, "v1", "revisada")
    diff = views_svc.diff_view_versions(db, p.tenant_id, "v1", 1, 2)
    modified = {m.id for m in diff.elements.modified}
    assert "a" in modified

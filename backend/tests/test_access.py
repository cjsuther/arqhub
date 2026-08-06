"""Authorization (SPEC §12): group folder visibility + draft privacy."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import Principal
from app.models import Base, Tenant, User
from app.schemas.api import ElementUpdate, FolderCreate, FolderLock, GroupCreate, ViewCreate, ViewInclude
from app.services import catalog, folders, groups, model_io
from app.services import views as views_svc

SEED = """
dsl: arqhub/1.0
model:
  elements:
    a: { name: A, kind: process }
    b: { name: B, kind: process }
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
    u1 = User(tenant_id=tenant.id, email="u1@x", display_name="Uno", role="editor")
    u2 = User(tenant_id=tenant.id, email="u2@x", display_name="Dos", role="viewer")
    db.add_all([admin, u1, u2])
    db.flush()
    p = Principal(user_id=admin.id, tenant_id=tenant.id, email=admin.email, role="admin")
    model_io.import_dsl(db, p, SEED, dry_run=False, replace=False)
    yield db, tenant, p, admin, u1, u2
    db.close()


def _pr(tenant, u):
    return Principal(user_id=u.id, tenant_id=tenant.id, email=u.email, role=u.role)


def _slugs(reads):
    return {e.slug for e in reads}


def test_folder_visibility_opt_in(ctx):
    db, tenant, p, admin, u1, u2 = ctx
    f = folders.create_folder(db, p, FolderCreate(name="Secreta", scope="element"))
    catalog.set_element_folder(db, p, "a", f.id)

    p1 = _pr(tenant, u1)
    # Public folder → everyone sees both.
    assert _slugs(catalog.list_elements(db, p1)) == {"a", "b"}

    # Restrict the folder to a group u1 is NOT in → 'a' disappears for u1, admin still sees it.
    g = groups.create_group(db, p, GroupCreate(name="Arquitectura"))
    groups.set_folder_groups(db, p, f.id, [g.id])
    assert _slugs(catalog.list_elements(db, p1)) == {"b"}
    assert _slugs(catalog.list_elements(db, p)) == {"a", "b"}  # admin bypass

    # Add u1 to the group → sees 'a' again.
    groups.set_user_groups(db, p, u1.id, [g.id])
    assert _slugs(catalog.list_elements(db, p1)) == {"a", "b"}


def test_folder_edit_lock(ctx):
    db, tenant, p, admin, u1, u2 = ctx  # u1 = editor
    p1 = _pr(tenant, u1)
    f = folders.create_folder(db, p, FolderCreate(name="Bloqueada", scope="element"))
    catalog.set_element_folder(db, p, "a", f.id)

    # Open: the editor can modify.
    catalog.update_element(db, p1, "a", ElementUpdate(description="v1"))

    # Lock to a group the editor is NOT in → denied; admin still allowed.
    g = groups.create_group(db, p, GroupCreate(name="Editores"))
    folders.set_folder_lock(db, p, f.id, FolderLock(locked=True, edit_group_id=g.id))
    with pytest.raises(Exception):
        catalog.update_element(db, p1, "a", ElementUpdate(description="nope"))
    catalog.update_element(db, p, "a", ElementUpdate(description="admin-ok"))

    # Add the editor to the group → allowed again.
    groups.set_user_groups(db, p, u1.id, [g.id])
    catalog.update_element(db, p1, "a", ElementUpdate(description="v2"))

    # Lock to nobody → even a group member (non-admin) is denied.
    folders.set_folder_lock(db, p, f.id, FolderLock(locked=True, edit_group_id=None))
    with pytest.raises(Exception):
        catalog.update_element(db, p1, "a", ElementUpdate(description="blocked"))


def test_draft_is_private_until_shared(ctx):
    db, tenant, p, admin, u1, u2 = ctx
    p1, p2 = _pr(tenant, u1), _pr(tenant, u2)
    views_svc.create_view(db, p1, ViewCreate(
        slug="mi-borrador", name="Mi borrador", lang="archimate",
        include=ViewInclude(elements=["a"]),
    ))
    # Author sees it; the other user does not; admin does.
    assert "mi-borrador" in {v.slug for v in views_svc.list_views(db, p1)}
    assert "mi-borrador" not in {v.slug for v in views_svc.list_views(db, p2)}
    assert "mi-borrador" in {v.slug for v in views_svc.list_views(db, p)}

    # Share with u2 → now visible to u2.
    views_svc.set_view_shares(db, p1, "mi-borrador", [u2.id])
    assert "mi-borrador" in {v.slug for v in views_svc.list_views(db, p2)}

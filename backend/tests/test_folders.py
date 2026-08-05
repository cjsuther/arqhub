"""Hierarchical folders (SPEC §8.1): CRUD, cycle guard, delete reparents."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import Principal
from app.models import Base, Element, Folder, Tenant
from app.schemas.api import FolderCreate, FolderUpdate
from app.services import folders


@pytest.fixture
def ctx():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    tenant = Tenant(slug="t", name="T", settings={})
    db.add(tenant)
    db.flush()
    p = Principal(user_id="u", tenant_id=tenant.id, email="a@b.c", role="admin")
    yield db, p
    db.close()


def test_create_and_list(ctx):
    db, p = ctx
    root = folders.create_folder(db, p, FolderCreate(name="Ventas", scope="element"))
    folders.create_folder(db, p, FolderCreate(name="Backend", scope="element", parent_id=root.id))
    folders.create_folder(db, p, FolderCreate(name="Procesos", scope="view"))
    assert len(folders.list_folders(db, p.tenant_id, "element")) == 2
    assert len(folders.list_folders(db, p.tenant_id, "view")) == 1


def test_move_and_cycle_guard(ctx):
    db, p = ctx
    a = folders.create_folder(db, p, FolderCreate(name="A", scope="element"))
    b = folders.create_folder(db, p, FolderCreate(name="B", scope="element", parent_id=a.id))
    # Moving A under B (its own child) must fail.
    with pytest.raises(Exception):
        folders.update_folder(db, p, a.id, FolderUpdate(parent_id=b.id))
    # Moving B to root is fine.
    moved = folders.update_folder(db, p, b.id, FolderUpdate(parent_id=None))
    assert moved.parent_id is None


def test_delete_reparents_children_and_items(ctx):
    db, p = ctx
    a = folders.create_folder(db, p, FolderCreate(name="A", scope="element"))
    b = folders.create_folder(db, p, FolderCreate(name="B", scope="element", parent_id=a.id))
    el = Element(tenant_id=p.tenant_id, slug="x", name="X", kind="process", folder_id=a.id)
    db.add(el)
    db.commit()
    folders.delete_folder(db, p, a.id)
    # B reparented to A's parent (root); element moved up too.
    assert db.get(Folder, b.id).parent_id is None
    assert db.scalar(select(Element).where(Element.slug == "x")).folder_id is None

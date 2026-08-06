"""Groups: CRUD, membership, folder visibility grants (SPEC §12)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import Principal
from app.models import Base, Folder, Tenant, User
from app.schemas.api import GroupCreate, GroupUpdate
from app.services import groups


@pytest.fixture
def ctx():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    tenant = Tenant(slug="t", name="T", settings={})
    db.add(tenant)
    db.flush()
    admin = User(tenant_id=tenant.id, email="a@x", display_name="Admin", role="admin")
    ana = User(tenant_id=tenant.id, email="ana@x", display_name="Ana", role="editor")
    beto = User(tenant_id=tenant.id, email="beto@x", display_name="Beto", role="viewer")
    folder = Folder(tenant_id=tenant.id, name="Aplicaciones", scope="element")
    db.add_all([admin, ana, beto, folder])
    db.flush()
    p = Principal(user_id=admin.id, tenant_id=tenant.id, email=admin.email, role="admin")
    yield db, p, {"ana": ana.id, "beto": beto.id, "folder": folder.id}
    db.close()


def test_create_update_delete(ctx):
    db, p, _ = ctx
    with pytest.raises(Exception):
        groups.create_group(db, p, GroupCreate(name="   "))
    g = groups.create_group(db, p, GroupCreate(name="Arquitectura"))
    assert g.name == "Arquitectura" and g.member_count == 0
    assert [x.name for x in groups.list_groups(db, p.tenant_id)] == ["Arquitectura"]

    g2 = groups.update_group(db, p, g.id, GroupUpdate(name="Arqui"))
    assert g2.name == "Arqui"

    groups.delete_group(db, p, g.id)
    assert groups.list_groups(db, p.tenant_id) == []


def test_missing_group_is_404(ctx):
    db, p, _ = ctx
    with pytest.raises(Exception):
        groups.update_group(db, p, "nope", GroupUpdate(name="x"))


def test_members_roundtrip_and_dedup(ctx):
    db, p, ids = ctx
    g = groups.create_group(db, p, GroupCreate(name="G"))
    read = groups.set_group_members(db, p, g.id, [ids["ana"], ids["ana"], ids["beto"], "ghost"])
    assert read.member_count == 2 and set(read.user_ids) == {ids["ana"], ids["beto"]}

    # membership is visible from the user side too
    refs = groups.groups_of_user(db, p.tenant_id, ids["ana"])
    assert [r.name for r in refs] == ["G"]


def test_set_user_groups(ctx):
    db, p, ids = ctx
    g1 = groups.create_group(db, p, GroupCreate(name="G1"))
    g2 = groups.create_group(db, p, GroupCreate(name="G2"))
    groups.set_user_groups(db, p, ids["ana"], [g1.id, g2.id])
    assert {r.name for r in groups.groups_of_user(db, p.tenant_id, ids["ana"])} == {"G1", "G2"}
    # replace, not append
    groups.set_user_groups(db, p, ids["ana"], [g2.id])
    assert {r.name for r in groups.groups_of_user(db, p.tenant_id, ids["ana"])} == {"G2"}


def test_set_user_groups_unknown_user_404(ctx):
    db, p, _ = ctx
    with pytest.raises(Exception):
        groups.set_user_groups(db, p, "ghost", [])


def test_folder_visibility_grants(ctx):
    db, p, ids = ctx
    g = groups.create_group(db, p, GroupCreate(name="G"))
    out = groups.set_folder_groups(db, p, ids["folder"], [g.id])
    assert out == [g.id]
    assert groups.get_folder_groups(db, p.tenant_id, ids["folder"]) == [g.id]


def test_folder_visibility_unknown_folder_404(ctx):
    db, p, _ = ctx
    with pytest.raises(Exception):
        groups.set_folder_groups(db, p, "ghost", [])

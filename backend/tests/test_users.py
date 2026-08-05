"""User administration (SPEC §12): create, role change, guards."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import Principal
from app.models import Base, Tenant, User
from app.schemas.api import UserCreate, UserUpdate
from app.services import users


@pytest.fixture
def ctx():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    tenant = Tenant(slug="t", name="T", settings={})
    db.add(tenant)
    db.flush()
    admin = User(tenant_id=tenant.id, email="admin@x", display_name="Admin", role="admin")
    db.add(admin)
    db.flush()
    p = Principal(user_id=admin.id, tenant_id=tenant.id, email=admin.email, role="admin")
    yield db, p, admin
    db.close()


def test_create_and_list(ctx):
    db, p, _ = ctx
    u = users.create_user(db, p, UserCreate(email="Ana@X.com", display_name="Ana", role="editor"))
    assert u.email == "ana@x.com" and u.role == "editor" and u.is_entra is False
    assert len(users.list_users(db, p.tenant_id)) == 2


def test_duplicate_email_conflicts(ctx):
    db, p, _ = ctx
    users.create_user(db, p, UserCreate(email="ana@x.com", display_name="Ana", role="viewer"))
    with pytest.raises(Exception):
        users.create_user(db, p, UserCreate(email="ANA@x.com", display_name="Otra", role="viewer"))


def test_invalid_role_rejected(ctx):
    db, p, _ = ctx
    with pytest.raises(Exception):
        users.create_user(db, p, UserCreate(email="z@x.com", display_name="Z", role="superuser"))


def test_update_role(ctx):
    db, p, _ = ctx
    u = users.create_user(db, p, UserCreate(email="ana@x.com", display_name="Ana", role="viewer"))
    updated = users.update_user(db, p, u.id, UserUpdate(role="approver"))
    assert updated.role == "approver"


def test_cannot_demote_last_admin(ctx):
    db, p, admin = ctx
    with pytest.raises(Exception):
        users.update_user(db, p, admin.id, UserUpdate(role="viewer"))


def test_cannot_delete_self_or_last_admin(ctx):
    db, p, admin = ctx
    with pytest.raises(Exception):
        users.delete_user(db, p, admin.id)


def test_delete_other_user(ctx):
    db, p, _ = ctx
    u = users.create_user(db, p, UserCreate(email="ana@x.com", display_name="Ana", role="viewer"))
    users.delete_user(db, p, u.id)
    assert len(users.list_users(db, p.tenant_id)) == 1

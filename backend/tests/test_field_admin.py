"""Custom field definitions: update/delete/get + guards (SPEC §4.1)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import Principal
from app.models import Base, Tenant, User
from app.schemas.api import FieldDefCreate, FieldDefUpdate
from app.services import field_defs


@pytest.fixture
def ctx():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    tenant = Tenant(slug="t", name="T", settings={})
    db.add(tenant)
    db.flush()
    admin = User(tenant_id=tenant.id, email="a@x", display_name="Admin", role="admin")
    db.add(admin)
    db.flush()
    p = Principal(user_id=admin.id, tenant_id=tenant.id, email=admin.email, role="admin")
    yield db, p
    db.close()


def test_create_requires_key(ctx):
    db, p = ctx
    with pytest.raises(Exception):
        field_defs.create_field(db, p, "process", FieldDefCreate(key="   ", label="X", field_type="text"))


def test_duplicate_key_conflicts(ctx):
    db, p = ctx
    field_defs.create_field(db, p, "process", FieldDefCreate(key="team", label="Equipo", field_type="text"))
    with pytest.raises(Exception):
        # slugifies to the same key -> 409
        field_defs.create_field(db, p, "process", FieldDefCreate(key="Team", label="Otro", field_type="text"))


def test_select_options_filter_blanks(ctx):
    db, p = ctx
    fd = field_defs.create_field(
        db, p, "process",
        FieldDefCreate(key="prio", label="Prioridad", field_type="select", options=["alta", "  ", "baja"]),
    )
    assert [o.strip() for o in fd.options] == ["alta", "baja"]


def test_update_field(ctx):
    db, p = ctx
    fd = field_defs.create_field(db, p, "process", FieldDefCreate(key="prio", label="Prioridad", field_type="text"))
    updated = field_defs.update_field(
        db, p, fd.id, FieldDefUpdate(label="Nivel", field_type="select", options=["hi", "lo"], position=2),
    )
    assert updated.label == "Nivel" and updated.field_type == "select"
    assert updated.options == ["hi", "lo"] and updated.position == 2


def test_update_invalid_type_rejected(ctx):
    db, p = ctx
    fd = field_defs.create_field(db, p, "process", FieldDefCreate(key="prio", label="Prioridad", field_type="text"))
    with pytest.raises(Exception):
        field_defs.update_field(db, p, fd.id, FieldDefUpdate(field_type="bogus"))


def test_update_missing_field_is_404(ctx):
    db, p = ctx
    with pytest.raises(Exception):
        field_defs.update_field(db, p, "does-not-exist", FieldDefUpdate(label="x"))


def test_delete_field(ctx):
    db, p = ctx
    fd = field_defs.create_field(db, p, "process", FieldDefCreate(key="prio", label="Prioridad", field_type="text"))
    field_defs.delete_field(db, p, fd.id)
    assert field_defs.list_fields(db, p.tenant_id, "process") == []
    with pytest.raises(Exception):
        field_defs.delete_field(db, p, fd.id)  # already gone -> 404

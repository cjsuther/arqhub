"""Custom fields per kind + search (SPEC §4.1)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import Principal
from app.models import Base, Tenant, User
from app.schemas.api import FieldDefCreate
from app.services import catalog, field_defs, model_io

SEED = """
dsl: arqhub/1.0
model:
  elements:
    a: { name: Alfa, kind: process }
    b: { name: Beta, kind: process }
"""


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
    model_io.import_dsl(db, p, SEED, dry_run=False, replace=False)
    yield db, p


def test_field_def_crud_and_values(ctx):
    db, p = ctx
    fd = field_defs.create_field(db, p, "process", FieldDefCreate(key="Owner Team", label="Equipo", field_type="text"))
    assert fd.key == "owner-team" and fd.field_type == "text"
    assert [f.key for f in field_defs.list_fields(db, p.tenant_id, "process")] == ["owner-team"]

    catalog.set_element_fields(db, p, "a", {"owner-team": "Pagos", "priority": 3})
    el = catalog.get_element(db, p.tenant_id, "a")
    assert el.custom_fields["owner-team"] == "Pagos" and el.custom_fields["priority"] == 3


def test_invalid_field_type_rejected(ctx):
    db, p = ctx
    with pytest.raises(Exception):
        field_defs.create_field(db, p, "process", FieldDefCreate(key="x", label="X", field_type="bogus"))


def test_search_by_field(ctx):
    db, p = ctx
    field_defs.create_field(db, p, "process", FieldDefCreate(key="team", label="Equipo", field_type="text"))
    catalog.set_element_fields(db, p, "a", {"team": "Riesgos"})
    catalog.set_element_fields(db, p, "b", {"team": "Canales"})

    hits = catalog.list_elements(db, p, field_key="team", field_value="ries")
    assert {e.slug for e in hits} == {"a"}
    # The generic text search also spans custom-field values.
    assert {e.slug for e in catalog.list_elements(db, p, q="canales")} == {"b"}

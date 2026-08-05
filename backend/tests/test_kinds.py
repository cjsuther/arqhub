"""Custom component kinds extending the registry matrix (SPEC §4.2)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import Principal
from app.models import Base
from app.schemas.api import KindCreate
from app.services import kind_registry
from app.services.dsl.graph import ModelGraph
from app.services.dsl.registry import Lifecycle, is_valid_kind
from app.services.dsl.graph import Element as GraphElement
from app.services.dsl.validator import validate_graph


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _p():
    return Principal(user_id="u", tenant_id="t", email="a@b.c", role="admin")


def test_add_custom_kind_extends_registry_and_validation(db):
    key = "data-store-test"
    try:
        snap = kind_registry.add_custom_kind(db, _p(), KindCreate(
            key=key, layer="technology", archimate="DataStore", uml="Node",
        ))
        assert key in snap["kinds"]
        assert snap["kinds"][key]["custom"] is True
        assert snap["kinds"][key]["mappings"]["bpmn"] is None  # only in some languages
        assert is_valid_kind(key)

        # An element of the custom kind now validates cleanly.
        g = ModelGraph()
        g.elements["x"] = GraphElement(slug="x", name="X", kind=key, lifecycle=Lifecycle.active)
        assert validate_graph(g).ok
    finally:
        kind_registry.delete_custom_kind(db, _p(), key)
        assert not is_valid_kind(key)


def test_cannot_delete_builtin(db):
    with pytest.raises(Exception):
        kind_registry.delete_custom_kind(db, _p(), "process")  # built-in


def test_requires_at_least_one_language(db):
    with pytest.raises(Exception):
        kind_registry.add_custom_kind(db, _p(), KindCreate(key="nope-test", layer="business"))

"""Personal access tokens for MCP auth (SPEC §9, §12)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import Principal
from app.models import Base, Tenant, User
from app.schemas.api import TokenCreate
from app.services import tokens


@pytest.fixture
def ctx():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    tenant = Tenant(slug="t", name="T", settings={})
    db.add(tenant)
    db.flush()
    u = User(tenant_id=tenant.id, email="u@x", display_name="U", role="editor")
    db.add(u)
    db.flush()
    p = Principal(user_id=u.id, tenant_id=tenant.id, email=u.email, role="editor")
    yield db, p, u


def test_create_authenticate_and_revoke(ctx):
    db, p, u = ctx
    created = tokens.create_token(db, p, TokenCreate(name="MCP"))
    assert created.token.startswith("arqhub_") and created.name == "MCP"
    assert len(tokens.list_tokens(db, p)) == 1

    princ = tokens.authenticate_token(db, created.token)
    assert princ is not None and princ.user_id == u.id and princ.role == "editor" and princ.actor_type == "mcp"

    assert tokens.authenticate_token(db, "arqhub_wrong") is None

    tokens.revoke_token(db, p, created.id)
    assert tokens.authenticate_token(db, created.token) is None
    assert len(tokens.list_tokens(db, p)) == 0

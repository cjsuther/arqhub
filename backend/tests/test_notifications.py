"""In-app notification feed (SPEC §11)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import Principal
from app.models import Base, Tenant, User
from app.services.notifications import store


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
    yield db, tenant, p, u
    db.close()


def test_record_list_and_mark_read(ctx):
    db, tenant, p, u = ctx
    store.record(db, tenant.id, [u.id], kind="comment_mention", title="Te mencionaron", body="hola", view_slug="v1")
    store.record(db, tenant.id, [u.id], kind="draft_shared", title="Compartido")

    assert store.unread_count(db, p) == 2
    items = store.list_notifications(db, p)
    assert len(items) == 2 and all(not n.read for n in items)

    store.mark_read(db, p, items[0].id)
    assert store.unread_count(db, p) == 1

    store.mark_all_read(db, p)
    assert store.unread_count(db, p) == 0


def test_record_skips_empty_recipients(ctx):
    db, tenant, p, u = ctx
    store.record(db, tenant.id, [], kind="x", title="nadie")
    store.record(db, tenant.id, [None], kind="x", title="nadie")
    assert store.unread_count(db, p) == 0

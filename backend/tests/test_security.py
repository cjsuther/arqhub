"""Security regressions: HTML sanitiser, dev-auth boot guard, automation gate,
directory email redaction."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import auth
from app.core.auth import Principal
from app.core.config import Settings
from app.core.deps import require_role
from app.models import Base, Tenant, User
from app.services.html_sanitize import sanitize_html


# --- HTML sanitiser (stored XSS) --------------------------------------------
def test_sanitizer_strips_script_and_handlers():
    dirty = '<p>hola<script>alert(1)</script></p><img src=x onerror="alert(2)">'
    clean = sanitize_html(dirty)
    assert "<script" not in clean and "onerror" not in clean and "<img" not in clean
    assert "hola" in clean and clean.startswith("<p>")


def test_sanitizer_keeps_allowlisted_formatting():
    clean = sanitize_html("<h3>T</h3><ul><li><strong>a</strong></li></ul>")
    assert clean == "<h3>T</h3><ul><li><strong>a</strong></li></ul>"


def test_sanitizer_drops_javascript_href_keeps_http():
    assert 'href' not in sanitize_html('<a href="javascript:alert(1)">x</a>')
    ok = sanitize_html('<a href="https://ok.test">x</a>')
    assert 'href="https://ok.test"' in ok and 'rel="noopener noreferrer"' in ok


def test_sanitizer_escapes_stray_markup_in_text():
    assert sanitize_html("a < b & c") == "a &lt; b &amp; c"


# --- dev_auth boot guard -----------------------------------------------------
def test_dev_auth_refused_on_non_sqlite(monkeypatch):
    cfg = Settings(dev_auth=True, allow_insecure_dev_auth=False,
                   database_url="postgresql+psycopg://u:p@db/arqhub")
    monkeypatch.setattr(auth, "settings", cfg)
    auth.reset_auth_provider()
    with pytest.raises(RuntimeError):
        auth.get_auth_provider()
    auth.reset_auth_provider()


def test_dev_auth_allowed_on_sqlite(monkeypatch):
    cfg = Settings(dev_auth=True, database_url="sqlite+pysqlite:///./x.db")
    monkeypatch.setattr(auth, "settings", cfg)
    auth.reset_auth_provider()
    assert isinstance(auth.get_auth_provider(), auth.DevAuthProvider)
    auth.reset_auth_provider()


def test_dev_auth_allowed_on_non_sqlite_with_explicit_override(monkeypatch):
    cfg = Settings(dev_auth=True, allow_insecure_dev_auth=True,
                   database_url="postgresql+psycopg://u:p@db/arqhub")
    monkeypatch.setattr(auth, "settings", cfg)
    auth.reset_auth_provider()
    assert isinstance(auth.get_auth_provider(), auth.DevAuthProvider)
    auth.reset_auth_provider()


# --- automation (MCP/PAT) gate on privileged actions -------------------------
def test_require_role_human_only_rejects_automation():
    dep = require_role("approver", human_only=True)
    mcp = Principal(user_id="u", tenant_id="t", email="e", role="admin", actor_type="mcp")
    with pytest.raises(Exception):
        dep(mcp)
    human = Principal(user_id="u", tenant_id="t", email="e", role="approver", actor_type="user")
    assert dep(human) is human


# --- directory email redaction ----------------------------------------------
@pytest.fixture
def api_ctx():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    t = Tenant(slug="t", name="T", settings={})
    db.add(t)
    db.flush()
    db.add_all([
        User(tenant_id=t.id, email="admin@x", display_name="Admin", role="admin"),
        User(tenant_id=t.id, email="viewer@x", display_name="Viewer", role="viewer"),
    ])
    db.commit()
    yield db, t
    db.close()


def test_non_admin_does_not_see_emails(api_ctx):
    from app.api.v1.users import list_users
    db, t = api_ctx
    viewer = Principal(user_id="v", tenant_id=t.id, email="viewer@x", role="viewer")
    admin = Principal(user_id="a", tenant_id=t.id, email="admin@x", role="admin")
    assert all(u.email == "" for u in list_users(db, viewer))
    assert any(u.email for u in list_users(db, admin))

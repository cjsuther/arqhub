"""Authentication (SPEC §12).

``AuthProvider`` is the seam that keeps the platform from being wedded to Azure.
Two implementations ship:

* ``DevAuthProvider`` — authenticates every request as the seed admin (dev only).
* ``EntraAuthProvider`` — validates real Entra ID (Azure AD) OIDC bearer tokens:
  RS256 signature against the tenant JWKS, issuer/audience/expiry checks, then
  just-in-time user provisioning and role mapping.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

import httpx
from fastapi import HTTPException, status
from jose import jwt
from jose.exceptions import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Tenant, User
from .config import Settings, settings

# Role precedence, low -> high (SPEC §12).
_ROLE_RANK = {"viewer": 0, "editor": 1, "approver": 2, "admin": 3}
_KNOWN_ROLES = set(_ROLE_RANK)


@dataclass(frozen=True)
class Principal:
    user_id: str
    tenant_id: str
    email: str
    role: str  # viewer|editor|approver|admin
    actor_type: str = "user"  # user|mcp|system


def ensure_seed(db: Session) -> tuple[Tenant, User]:
    """Ensure the default tenant and a dev admin user exist."""
    tenant = db.scalar(select(Tenant).where(Tenant.slug == settings.default_tenant_slug))
    if tenant is None:
        tenant = Tenant(slug=settings.default_tenant_slug, name=settings.default_tenant_name, settings={})
        db.add(tenant)
        db.flush()

    admin = db.scalar(select(User).where(User.tenant_id == tenant.id, User.role == "admin"))
    if admin is None:
        admin = User(
            tenant_id=tenant.id, email="admin@arqhub.local", display_name="Dev Admin", role="admin"
        )
        db.add(admin)
        db.flush()

    # A few sample approvers so the review picklist has options in dev.
    if settings.dev_auth:
        for email, name, role in (
            ("ana@arqhub.local", "Ana Aprobadora", "approver"),
            ("beto@arqhub.local", "Beto Revisor", "approver"),
            ("caro@arqhub.local", "Caro Editora", "editor"),
        ):
            if db.scalar(select(User).where(User.tenant_id == tenant.id, User.email == email)) is None:
                db.add(User(tenant_id=tenant.id, email=email, display_name=name, role=role))
    db.commit()
    return tenant, admin


def _bearer_required(token: str | None) -> str:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


class AuthProvider(ABC):
    @abstractmethod
    def authenticate(self, db: Session, token: str | None) -> Principal: ...


class DevAuthProvider(AuthProvider):
    """Authenticates as the seed admin — dev only, never for prod."""

    def authenticate(self, db: Session, token: str | None) -> Principal:
        tenant, admin = ensure_seed(db)
        return Principal(user_id=admin.id, tenant_id=tenant.id, email=admin.email, role=admin.role)


class EntraAuthProvider(AuthProvider):
    """Validates Entra ID OIDC bearer tokens and provisions users (SPEC §12)."""

    def __init__(
        self,
        cfg: Settings,
        jwks_loader: Callable[[], list[dict]] | None = None,
        jwks_ttl: float = 3600.0,
    ) -> None:
        self.audience = cfg.entra_client_id
        self.issuer = cfg.entra_effective_issuer()
        self.jwks_uri = cfg.entra_effective_jwks_uri()
        self.role_map = dict(cfg.entra_role_map)
        self.default_role = cfg.default_role
        self._jwks_loader = jwks_loader or self._fetch_jwks
        self._jwks_ttl = jwks_ttl
        self._keys: list[dict] = []
        self._fetched_at = 0.0

    # --- JWKS (cached, refreshed on TTL or unknown kid) ----------------------
    def _fetch_jwks(self) -> list[dict]:
        resp = httpx.get(self.jwks_uri, timeout=10.0)
        resp.raise_for_status()
        return resp.json().get("keys", [])

    def _signing_key(self, kid: str) -> dict | None:
        now = time.time()
        if not self._keys or now - self._fetched_at > self._jwks_ttl:
            self._keys = self._jwks_loader()
            self._fetched_at = now
        key = next((k for k in self._keys if k.get("kid") == kid), None)
        if key is None:  # possible key rotation — force one refresh
            self._keys = self._jwks_loader()
            self._fetched_at = now
            key = next((k for k in self._keys if k.get("kid") == kid), None)
        return key

    # --- Role mapping (app roles + group ids -> ArqHub role) ------------------
    def _resolve_role(self, claims: dict) -> str:
        best = self.default_role
        candidates = list(claims.get("roles", [])) + list(claims.get("groups", []))
        for c in candidates:
            mapped = c if c in _KNOWN_ROLES else self.role_map.get(c)
            if mapped in _KNOWN_ROLES and _ROLE_RANK[mapped] > _ROLE_RANK[best]:
                best = mapped
        return best

    def authenticate(self, db: Session, token: str | None) -> Principal:
        token = _bearer_required(token)
        try:
            header = jwt.get_unverified_header(token)
        except JWTError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed token.") from exc

        key = self._signing_key(header.get("kid", ""))
        if key is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown signing key.")

        try:
            claims = jwt.decode(
                token, key, algorithms=["RS256"], audience=self.audience, issuer=self.issuer
            )
        except JWTError as exc:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}") from exc

        oid = claims.get("oid") or claims.get("sub")
        if not oid:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token has no subject.")
        email = claims.get("preferred_username") or claims.get("email") or oid
        name = claims.get("name") or email
        role = self._resolve_role(claims)

        tenant, _ = ensure_seed(db)
        user = self._provision(db, tenant.id, oid=oid, email=email, name=name, role=role)
        return Principal(user_id=user.id, tenant_id=tenant.id, email=user.email, role=user.role)

    @staticmethod
    def _provision(db: Session, tenant_id: str, *, oid: str, email: str, name: str, role: str) -> User:
        """Just-in-time provisioning: upsert the user by Entra object id."""
        user = db.scalar(select(User).where(User.tenant_id == tenant_id, User.entra_oid == oid))
        if user is None:
            user = User(tenant_id=tenant_id, entra_oid=oid, email=email, display_name=name, role=role)
            db.add(user)
        else:
            user.email, user.display_name, user.role = email, name, role
        db.commit()
        return user


_provider: AuthProvider | None = None


def get_auth_provider() -> AuthProvider:
    """Return the process-wide provider (caches the Entra JWKS between requests)."""
    global _provider
    if _provider is None:
        if settings.dev_auth:
            # dev_auth authenticates every request as admin with no token. Allow it
            # freely on SQLite (local dev), but refuse on a real database unless the
            # operator explicitly opted in — avoids shipping an open API by accident.
            if not settings.database_url.startswith("sqlite") and not settings.allow_insecure_dev_auth:
                raise RuntimeError(
                    "ARQHUB_DEV_AUTH=true on a non-SQLite database authenticates every "
                    "request as admin with no token. Refusing to start. Set "
                    "ARQHUB_DEV_AUTH=false and configure Entra ID, or set "
                    "ARQHUB_ALLOW_INSECURE_DEV_AUTH=true to override for a trusted demo."
                )
            _provider = DevAuthProvider()
        elif settings.entra_client_id and settings.entra_effective_jwks_uri():
            _provider = EntraAuthProvider(settings)
        else:
            raise RuntimeError(
                "dev_auth is false but Entra ID is not configured "
                "(set ARQHUB_ENTRA_CLIENT_ID and ARQHUB_ENTRA_TENANT_ID)."
            )
    return _provider


def reset_auth_provider() -> None:
    """Test hook: drop the cached provider so settings changes take effect."""
    global _provider
    _provider = None

"""Entra ID OIDC provider (SPEC §12): signature/issuer/audience validation,
role mapping and JIT provisioning — verified with a self-signed RS256 token."""

import time

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from jose import jwk as jose_jwk
from jose import jwt
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.auth import EntraAuthProvider
from app.core.config import Settings
from app.models import Base, User

AUDIENCE = "api://arqhub"
ISSUER = "https://issuer.test/v2.0"
KID = "test-key-1"


def _keypair():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    pub_pem = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    jwk_dict = jose_jwk.construct(pub_pem, "RS256").to_dict()
    jwk_dict.update(kid=KID, alg="RS256", use="sig")
    return priv_pem, jwk_dict


PRIV_PEM, PUBLIC_JWK = _keypair()
OTHER_PRIV_PEM, _ = _keypair()


def _mint(priv=PRIV_PEM, **overrides) -> str:
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "oid": "oid-abc",
        "preferred_username": "ana@bna.local",
        "name": "Ana Perez",
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    return jwt.encode(claims, priv, algorithm="RS256", headers={"kid": KID})


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


@pytest.fixture
def provider():
    cfg = Settings(
        dev_auth=False,
        entra_client_id=AUDIENCE,
        entra_issuer=ISSUER,
        entra_jwks_uri="https://issuer.test/keys",
        entra_role_map={"grp-approvers": "approver"},
    )
    return EntraAuthProvider(cfg, jwks_loader=lambda: [PUBLIC_JWK])


def test_valid_token_provisions_user(db, provider):
    p = provider.authenticate(db, _mint(roles=["editor"]))
    assert p.email == "ana@bna.local"
    assert p.role == "editor"
    user = db.scalar(select(User).where(User.entra_oid == "oid-abc"))
    assert user is not None and user.display_name == "Ana Perez"


def test_second_login_updates_not_duplicates(db, provider):
    provider.authenticate(db, _mint(roles=["editor"]))
    p = provider.authenticate(db, _mint(roles=["admin"]))
    assert p.role == "admin"
    assert len(db.scalars(select(User).where(User.entra_oid == "oid-abc")).all()) == 1


def test_group_maps_to_role(db, provider):
    p = provider.authenticate(db, _mint(groups=["grp-approvers"]))
    assert p.role == "approver"


def test_highest_role_wins(db, provider):
    p = provider.authenticate(db, _mint(roles=["viewer", "admin", "editor"]))
    assert p.role == "admin"


def test_no_roles_defaults_to_viewer(db, provider):
    assert provider.authenticate(db, _mint()).role == "viewer"


def test_wrong_audience_rejected(db, provider):
    with pytest.raises(HTTPException) as exc:
        provider.authenticate(db, _mint(aud="api://intruder"))
    assert exc.value.status_code == 401


def test_expired_token_rejected(db, provider):
    now = int(time.time())
    with pytest.raises(HTTPException) as exc:
        provider.authenticate(db, _mint(iat=now - 7200, exp=now - 3600))
    assert exc.value.status_code == 401


def test_bad_signature_rejected(db, provider):
    # Signed with a different key but the same kid -> signature check must fail.
    with pytest.raises(HTTPException) as exc:
        provider.authenticate(db, _mint(priv=OTHER_PRIV_PEM))
    assert exc.value.status_code == 401


def test_missing_token_rejected(db, provider):
    with pytest.raises(HTTPException) as exc:
        provider.authenticate(db, None)
    assert exc.value.status_code == 401

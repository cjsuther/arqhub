"""Application settings (env-driven, SPEC §12: secrets via env, never in repo)."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ARQHUB_", env_file=".env", extra="ignore")

    # SQLite by default so the stack runs with zero infra; Postgres in prod
    # (e.g. postgresql+psycopg://user:pass@host/arqhub).
    database_url: str = "sqlite+pysqlite:///./arqhub.db"

    # Dev auth stub: when true, requests are authenticated as the seed admin.
    # Set false in prod to require real Entra ID OIDC bearer tokens.
    dev_auth: bool = True

    # Entra ID (Azure AD) OIDC — SPEC §12. Required when dev_auth is false.
    entra_tenant_id: str | None = None
    entra_client_id: str | None = None  # token audience (api://... or app id)
    entra_issuer: str | None = None  # e.g. https://login.microsoftonline.com/{tid}/v2.0
    entra_jwks_uri: str | None = None  # discovery keys endpoint
    # Map an Entra app-role name or group object id -> ArqHub role.
    entra_role_map: dict[str, str] = {}
    default_role: str = "viewer"

    default_tenant_slug: str = "demo"
    default_tenant_name: str = "Demo Org"

    # Redis for the arq job worker (exports, notifications, daily snapshots — §11).
    redis_url: str = "redis://localhost:6379"

    # Rate limiting (§9/§12). Off by default so dev/tests are unthrottled.
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 120

    api_prefix: str = "/api/v1"

    def entra_effective_issuer(self) -> str | None:
        if self.entra_issuer:
            return self.entra_issuer
        if self.entra_tenant_id:
            return f"https://login.microsoftonline.com/{self.entra_tenant_id}/v2.0"
        return None

    def entra_effective_jwks_uri(self) -> str | None:
        if self.entra_jwks_uri:
            return self.entra_jwks_uri
        if self.entra_tenant_id:
            return f"https://login.microsoftonline.com/{self.entra_tenant_id}/discovery/v2.0/keys"
        return None


settings = Settings()

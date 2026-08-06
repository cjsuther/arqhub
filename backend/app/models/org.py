"""Tenant, User and Domain (SPEC §6, §12)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, PkMixin, TenantMixin, TimestampMixin


class Tenant(Base, PkMixin, TimestampMixin):
    __tablename__ = "tenants"

    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    settings: Mapped[dict] = mapped_column(default=dict)


class User(Base, PkMixin, TenantMixin, TimestampMixin):
    __tablename__ = "users"

    entra_oid: Mapped[str | None] = mapped_column(String(64), index=True, default=None)
    email: Mapped[str] = mapped_column(String(255), index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="viewer")  # viewer|editor|approver|admin


class Domain(Base, PkMixin, TenantMixin, TimestampMixin):
    __tablename__ = "domains"

    slug: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    ad_group_id: Mapped[str | None] = mapped_column(String(64), default=None)


class ApiToken(Base, PkMixin, TenantMixin, TimestampMixin):
    """A personal access token a user manages from their profile — used to
    authenticate the MCP server (or scripts) as that user (SPEC §9, §12).

    Only the SHA-256 hash is stored; the plaintext is shown once at creation.
    """

    __tablename__ = "api_tokens"

    user_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(255))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    prefix: Mapped[str] = mapped_column(String(16))  # first chars, for display
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class Group(Base, PkMixin, TenantMixin, TimestampMixin):
    """A named set of users used to grant folder visibility (SPEC §12)."""

    __tablename__ = "groups"

    name: Mapped[str] = mapped_column(String(255))


class UserGroup(Base, PkMixin, TenantMixin, TimestampMixin):
    """Membership: a user belongs to many groups, a group has many users."""

    __tablename__ = "user_groups"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id"), index=True)


class GroupFolder(Base, PkMixin, TenantMixin, TimestampMixin):
    """Visibility grant: a group can see a folder (and its contents)."""

    __tablename__ = "group_folders"

    group_id: Mapped[str] = mapped_column(String(36), ForeignKey("groups.id"), index=True)
    folder_id: Mapped[str] = mapped_column(String(36), ForeignKey("folders.id"), index=True)


class Folder(Base, PkMixin, TenantMixin, TimestampMixin):
    """Hierarchical folder for organising the catalog and views (presentation).

    Two independent trees per tenant via ``scope`` ('element' | 'view'). Purely
    organisational — not part of the semantic model / DSL.
    """

    __tablename__ = "folders"

    name: Mapped[str] = mapped_column(String(255))
    scope: Mapped[str] = mapped_column(String(16), index=True)  # element | view
    parent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("folders.id"), default=None, index=True
    )
    # Edit lock (SPEC §12): when locked, only members of ``edit_group_id`` (or, when
    # null, nobody but admins) may modify the folder and the items inside it.
    locked: Mapped[bool] = mapped_column(default=False)
    edit_group_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("groups.id"), default=None)

"""Tenant, User and Domain (SPEC §6, §12)."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
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

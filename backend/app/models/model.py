"""The living model: Element, Relationship, View, ViewLayout, ModelVersion (SPEC §6).

``slug`` is the stable, LLM-facing id (unique per tenant + entity). Elements and
relationships use soft delete because they may appear in published views.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, PkMixin, TenantMixin, TimestampMixin


class Element(Base, PkMixin, TenantMixin, TimestampMixin):
    __tablename__ = "elements"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_element_tenant_slug"),)

    slug: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(255))
    kind: Mapped[str] = mapped_column(String(32), index=True)
    domain_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("domains.id"), default=None)
    owner_id: Mapped[str | None] = mapped_column(String(36), default=None)
    description: Mapped[str | None] = mapped_column(String, default=None)
    lifecycle: Mapped[str] = mapped_column(String(16), default="active")
    tags: Mapped[list] = mapped_column(default=list)
    properties: Mapped[dict] = mapped_column(default=dict)
    mappings: Mapped[dict] = mapped_column(default=dict)
    folder_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("folders.id"), default=None, index=True)
    deleted_at: Mapped[str | None] = mapped_column(String(32), default=None, index=True)


class Relationship(Base, PkMixin, TenantMixin, TimestampMixin):
    __tablename__ = "relationships"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_relationship_tenant_slug"),)

    slug: Mapped[str] = mapped_column(String(256), index=True)
    from_element: Mapped[str] = mapped_column(String(128), index=True)  # element slug
    to_element: Mapped[str] = mapped_column(String(128), index=True)  # element slug
    kind: Mapped[str] = mapped_column(String(32))
    label: Mapped[str | None] = mapped_column(String(255), default=None)
    properties: Mapped[dict] = mapped_column(default=dict)
    deleted_at: Mapped[str | None] = mapped_column(String(32), default=None, index=True)


class View(Base, PkMixin, TenantMixin, TimestampMixin):
    __tablename__ = "views"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_view_tenant_slug"),)

    slug: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(255))
    lang: Mapped[str] = mapped_column(String(16))
    viewpoint: Mapped[str | None] = mapped_column(String(64), default=None)
    include: Mapped[dict] = mapped_column(default=dict)  # {elements: [...], relations: auto|[...]}
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft|in_review|published|deprecated
    # Who moved the view to its current status, and when (SPEC §11).
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    status_changed_by: Mapped[str | None] = mapped_column(String(36), default=None)
    # Author — a draft is private to its creator + explicit shares (SPEC §12).
    created_by: Mapped[str | None] = mapped_column(String(36), default=None)
    current_version: Mapped[int] = mapped_column(Integer, default=0)
    folder_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("folders.id"), default=None, index=True)
    # Rich-text documentation (HTML from the WYSIWYG editor), presentation-side.
    notes: Mapped[str | None] = mapped_column(String, default=None)


class ViewLayout(Base, PkMixin, TenantMixin, TimestampMixin):
    """Presentation only — positions, kept out of the model (SPEC §1, §6)."""

    __tablename__ = "view_layouts"

    view_id: Mapped[str] = mapped_column(String(36), ForeignKey("views.id"), index=True)
    element_slug: Mapped[str] = mapped_column(String(128))
    x: Mapped[float] = mapped_column(default=0.0)
    y: Mapped[float] = mapped_column(default=0.0)
    w: Mapped[float] = mapped_column(default=0.0)
    h: Mapped[float] = mapped_column(default=0.0)
    # Pool/lane the node is nested in (element slug), presentation-side (SPEC §8.2).
    parent: Mapped[str | None] = mapped_column(String(128), default=None)
    style: Mapped[dict] = mapped_column(default=dict)


class Comment(Base, PkMixin, TenantMixin, TimestampMixin):
    """User comment thread on a view (SPEC §11 collaboration)."""

    __tablename__ = "comments"

    view_id: Mapped[str] = mapped_column(String(36), ForeignKey("views.id"), index=True)
    author_id: Mapped[str | None] = mapped_column(String(36), default=None)
    body: Mapped[str] = mapped_column(String)


class ViewShare(Base, PkMixin, TenantMixin, TimestampMixin):
    """A user the draft view is shared with, beyond its author (SPEC §12)."""

    __tablename__ = "view_shares"

    view_id: Mapped[str] = mapped_column(String(36), ForeignKey("views.id"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)


class ModelVersion(Base, PkMixin, TenantMixin, TimestampMixin):
    """Snapshot of the DSL for a scope (whole model or one view) — SPEC §6, §11."""

    __tablename__ = "model_versions"

    scope: Mapped[str] = mapped_column(String(16))  # model|view
    scope_id: Mapped[str | None] = mapped_column(String(128), default=None)  # view slug when scope=view
    version: Mapped[int] = mapped_column(Integer)
    snapshot: Mapped[dict] = mapped_column(default=dict)  # DSL doc as dict
    message: Mapped[str | None] = mapped_column(String(512), default=None)
    author_id: Mapped[str | None] = mapped_column(String(36), default=None)

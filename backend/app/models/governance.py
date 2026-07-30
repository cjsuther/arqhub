"""ApprovalRequest and the append-only AuditLog (SPEC §6, §11, §12)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, PkMixin, TenantMixin, TimestampMixin


class ApprovalRequest(Base, PkMixin, TenantMixin, TimestampMixin):
    __tablename__ = "approval_requests"

    view_id: Mapped[str] = mapped_column(String(36), ForeignKey("views.id"), index=True)
    view_version: Mapped[int] = mapped_column(Integer)
    requested_by: Mapped[str | None] = mapped_column(String(36), default=None)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|approved|rejected|cancelled
    approvers: Mapped[list] = mapped_column(default=list)
    resolved_by: Mapped[str | None] = mapped_column(String(36), default=None)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    comment: Mapped[str | None] = mapped_column(String(1024), default=None)
    teams_message_id: Mapped[str | None] = mapped_column(String(128), default=None)


class AuditLog(Base, PkMixin, TenantMixin):
    """Append-only trace of every mutation, human or IA (SPEC §6, §12)."""

    __tablename__ = "audit_log"

    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), default=None)
    actor_type: Mapped[str] = mapped_column(String(16), default="user")  # user|mcp|system
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str | None] = mapped_column(String(128), default=None)
    payload: Mapped[dict] = mapped_column(default=dict)

"""Persisted in-app notification feed (SPEC §11).

Recording is best-effort: it commits its own rows after the caller's main
transaction, so a notification failure never rolls back the underlying action.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ...core.auth import Principal
from ...models import Notification
from ...schemas.api import NotificationRead


def record(db: Session, tenant_id: str, user_ids, *, kind: str, title: str,
           body: str = "", view_slug: str | None = None) -> None:
    recipients = [u for u in dict.fromkeys(user_ids) if u]
    if not recipients:
        return
    for uid in recipients:
        db.add(Notification(tenant_id=tenant_id, user_id=uid, kind=kind,
                            title=title, body=body or "", view_slug=view_slug))
    db.commit()


def _read(n: Notification) -> NotificationRead:
    return NotificationRead(
        id=n.id, kind=n.kind, title=n.title, body=n.body or "",
        view_slug=n.view_slug, read=bool(n.read),
        created_at=n.created_at.isoformat() if n.created_at else "",
    )


def list_notifications(db: Session, principal: Principal, unread_only: bool = False) -> list[NotificationRead]:
    q = select(Notification).where(
        Notification.tenant_id == principal.tenant_id, Notification.user_id == principal.user_id
    )
    if unread_only:
        q = q.where(Notification.read.is_(False))
    q = q.order_by(Notification.created_at.desc()).limit(200)
    return [_read(n) for n in db.scalars(q).all()]


def unread_count(db: Session, principal: Principal) -> int:
    from sqlalchemy import func
    return db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.tenant_id == principal.tenant_id,
            Notification.user_id == principal.user_id,
            Notification.read.is_(False),
        )
    ) or 0


def mark_read(db: Session, principal: Principal, notif_id: str) -> None:
    n = db.get(Notification, notif_id)
    if n is None or n.tenant_id != principal.tenant_id or n.user_id != principal.user_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notificación no encontrada.")
    n.read = True
    db.commit()


def mark_all_read(db: Session, principal: Principal) -> None:
    db.execute(
        update(Notification)
        .where(Notification.tenant_id == principal.tenant_id, Notification.user_id == principal.user_id)
        .values(read=True)
    )
    db.commit()

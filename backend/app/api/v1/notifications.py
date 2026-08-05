"""In-app notification feed endpoints (SPEC §11)."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from ...core.deps import DbDep, PrincipalDep
from ...schemas.api import NotificationRead
from ...services.notifications import store

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationRead])
def list_notifications(db: DbDep, principal: PrincipalDep, unread_only: bool = False):
    return store.list_notifications(db, principal, unread_only)


@router.get("/unread-count", response_model=int)
def unread_count(db: DbDep, principal: PrincipalDep):
    return store.unread_count(db, principal)


@router.post("/{notif_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(db: DbDep, principal: PrincipalDep, notif_id: str):
    store.mark_read(db, principal, notif_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(db: DbDep, principal: PrincipalDep):
    store.mark_all_read(db, principal)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

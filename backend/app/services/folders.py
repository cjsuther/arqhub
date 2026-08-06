"""Hierarchical folders for organising the catalog and views (SPEC §8.1, presentation).

Two independent trees per tenant via ``scope`` ('element' | 'view'). Folders are
organisational metadata — not part of the semantic model / DSL.
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.auth import Principal
from ..core.deps import write_audit
from ..models import Element, Folder, View
from ..schemas.api import FolderCreate, FolderLock, FolderRead, FolderUpdate
from . import access


def _read(f: Folder) -> FolderRead:
    return FolderRead(
        id=f.id, name=f.name, scope=f.scope, parent_id=f.parent_id,
        locked=bool(f.locked), edit_group_id=f.edit_group_id,
    )


def _get(db: Session, tenant_id: str, folder_id: str) -> Folder:
    f = db.get(Folder, folder_id)
    if f is None or f.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder not found.")
    return f


def list_folders(db: Session, tenant_id: str, scope: str | None = None) -> list[FolderRead]:
    q = select(Folder).where(Folder.tenant_id == tenant_id)
    if scope:
        q = q.where(Folder.scope == scope)
    return [_read(f) for f in db.scalars(q.order_by(Folder.name))]


def create_folder(db: Session, principal: Principal, payload: FolderCreate) -> FolderRead:
    if payload.scope not in ("element", "view"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "scope must be 'element' or 'view'.")
    if payload.parent_id:
        _get(db, principal.tenant_id, payload.parent_id)  # validate parent exists
    f = Folder(
        tenant_id=principal.tenant_id, name=payload.name, scope=payload.scope, parent_id=payload.parent_id
    )
    db.add(f)
    write_audit(db, principal, action="create", entity="folder", entity_id=f.name)
    db.commit()
    return _read(f)


def _is_descendant(db: Session, folder_id: str, maybe_ancestor: str) -> bool:
    """True if maybe_ancestor is folder_id or one of its descendants (cycle guard)."""
    cur: str | None = maybe_ancestor
    seen = set()
    while cur:
        if cur == folder_id:
            return True
        if cur in seen:
            break
        seen.add(cur)
        f = db.get(Folder, cur)
        cur = f.parent_id if f else None
    return False


def set_folder_lock(db: Session, principal: Principal, folder_id: str, payload: FolderLock) -> FolderRead:
    f = _get(db, principal.tenant_id, folder_id)
    f.locked = payload.locked
    f.edit_group_id = payload.edit_group_id if payload.locked else None
    write_audit(db, principal, action="lock", entity="folder", entity_id=folder_id,
                payload={"locked": payload.locked, "group": payload.edit_group_id})
    db.commit()
    return _read(f)


def update_folder(db: Session, principal: Principal, folder_id: str, payload: FolderUpdate) -> FolderRead:
    f = _get(db, principal.tenant_id, folder_id)
    access.assert_can_edit_folder(db, principal, folder_id)  # respect the edit lock
    changes = payload.model_dump(exclude_unset=True)
    if "parent_id" in changes:
        new_parent = changes["parent_id"]
        if new_parent == folder_id or (new_parent and _is_descendant(db, folder_id, new_parent)):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot move a folder into itself or a descendant.")
        if new_parent:
            _get(db, principal.tenant_id, new_parent)
    for k, v in changes.items():
        setattr(f, k, v)
    write_audit(db, principal, action="update", entity="folder", entity_id=folder_id)
    db.commit()
    return _read(f)


def delete_folder(db: Session, principal: Principal, folder_id: str) -> None:
    f = _get(db, principal.tenant_id, folder_id)
    access.assert_can_edit_folder(db, principal, folder_id)  # respect the edit lock
    # Reparent children and move contained items up to this folder's parent.
    for child in db.scalars(select(Folder).where(Folder.parent_id == folder_id)):
        child.parent_id = f.parent_id
    Model = Element if f.scope == "element" else View
    for item in db.scalars(
        select(Model).where(Model.tenant_id == principal.tenant_id, Model.folder_id == folder_id)
    ):
        item.folder_id = f.parent_id
    db.delete(f)
    write_audit(db, principal, action="delete", entity="folder", entity_id=folder_id)
    db.commit()

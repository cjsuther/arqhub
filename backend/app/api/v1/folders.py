"""Folder endpoints (SPEC §8.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from ...core.deps import DbDep, PrincipalDep, require_role
from ...schemas.api import FolderCreate, FolderLock, FolderRead, FolderUpdate, IdList
from ...services import folders, groups

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get("", response_model=list[FolderRead])
def list_folders(db: DbDep, principal: PrincipalDep, scope: str | None = None):
    return folders.list_folders(db, principal.tenant_id, scope)


@router.post("", response_model=FolderRead, status_code=status.HTTP_201_CREATED)
def create_folder(db: DbDep, payload: FolderCreate, principal=Depends(require_role("editor"))):
    return folders.create_folder(db, principal, payload)


@router.patch("/{folder_id}", response_model=FolderRead)
def update_folder(db: DbDep, folder_id: str, payload: FolderUpdate, principal=Depends(require_role("editor"))):
    return folders.update_folder(db, principal, folder_id, payload)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(db: DbDep, folder_id: str, principal=Depends(require_role("editor"))):
    folders.delete_folder(db, principal, folder_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Folder visibility: which groups can see this folder (SPEC §12) ----------
@router.get("/{folder_id}/groups", response_model=list[str])
def get_folder_groups(db: DbDep, principal: PrincipalDep, folder_id: str):
    return groups.get_folder_groups(db, principal.tenant_id, folder_id)


@router.put("/{folder_id}/groups", response_model=list[str])
def set_folder_groups(db: DbDep, folder_id: str, body: IdList, principal=Depends(require_role("admin"))):
    return groups.set_folder_groups(db, principal, folder_id, body.ids)


@router.put("/{folder_id}/lock", response_model=FolderRead)
def set_folder_lock(db: DbDep, folder_id: str, body: FolderLock, principal=Depends(require_role("admin"))):
    return folders.set_folder_lock(db, principal, folder_id, body)

"""Folder endpoints (SPEC §8.1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from ...core.deps import DbDep, PrincipalDep, require_role
from ...schemas.api import FolderCreate, FolderRead, FolderUpdate
from ...services import folders

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

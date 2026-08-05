"""Group endpoints — folder-visibility groups (SPEC §12)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from ...core.deps import DbDep, PrincipalDep, require_role
from ...schemas.api import GroupCreate, GroupRead, GroupUpdate
from ...services import groups

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("", response_model=list[GroupRead])
def list_groups(db: DbDep, principal: PrincipalDep):
    return groups.list_groups(db, principal.tenant_id)


@router.post("", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(db: DbDep, payload: GroupCreate, principal=Depends(require_role("admin"))):
    return groups.create_group(db, principal, payload)


@router.patch("/{group_id}", response_model=GroupRead)
def update_group(db: DbDep, group_id: str, payload: GroupUpdate, principal=Depends(require_role("admin"))):
    return groups.update_group(db, principal, group_id, payload)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(db: DbDep, group_id: str, principal=Depends(require_role("admin"))):
    groups.delete_group(db, principal, group_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

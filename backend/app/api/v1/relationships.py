"""Relationship endpoints (SPEC §7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from ...core.deps import DbDep, PrincipalDep, require_role
from ...schemas.api import RelationshipCreate, RelationshipRead, RelationshipUpdate
from ...services import catalog

router = APIRouter(prefix="/relationships", tags=["relationships"])


@router.get("", response_model=list[RelationshipRead])
def list_relationships(db: DbDep, principal: PrincipalDep):
    return catalog.list_relationships(db, principal.tenant_id)


@router.post("", response_model=RelationshipRead, status_code=status.HTTP_201_CREATED)
def create_relationship(db: DbDep, payload: RelationshipCreate, principal=Depends(require_role("editor"))):
    return catalog.create_relationship(db, principal, payload)


@router.patch("/{slug}", response_model=RelationshipRead)
def update_relationship(db: DbDep, slug: str, payload: RelationshipUpdate, principal=Depends(require_role("editor"))):
    return catalog.update_relationship(db, principal, slug, payload)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_relationship(db: DbDep, slug: str, principal=Depends(require_role("editor"))):
    catalog.delete_relationship(db, principal, slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

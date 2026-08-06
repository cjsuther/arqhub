"""Element catalog endpoints (SPEC §7)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from ...core.deps import DbDep, PrincipalDep, require_role
from ...schemas.api import ElementCreate, ElementRead, ElementUpdate, FieldValues, FolderAssign
from ...services import catalog, graph_ops
from ...services.graph_ops import ImpactResult

router = APIRouter(prefix="/elements", tags=["elements"])


@router.get("", response_model=list[ElementRead])
def list_elements(
    db: DbDep,
    principal: PrincipalDep,
    kind: str | None = None,
    domain: str | None = None,
    lifecycle: str | None = None,
    tag: str | None = None,
    q: str | None = None,
    field_key: str | None = None,
    field_value: str | None = None,
):
    return catalog.list_elements(
        db, principal, kind=kind, domain=domain, lifecycle=lifecycle, tag=tag, q=q,
        field_key=field_key, field_value=field_value,
    )


@router.get("/{slug}", response_model=ElementRead)
def get_element(db: DbDep, principal: PrincipalDep, slug: str):
    return catalog.get_element(db, principal.tenant_id, slug)


@router.get("/{slug}/views")
def element_views(db: DbDep, principal: PrincipalDep, slug: str) -> list[dict]:
    return graph_ops.element_views(db, principal.tenant_id, slug)


@router.get("/{slug}/impact", response_model=ImpactResult)
def element_impact(
    db: DbDep, principal: PrincipalDep, slug: str, depth: int = 2, directed: bool = True
):
    return graph_ops.impact(db, principal.tenant_id, slug, depth=depth, directed=directed)


@router.post("", response_model=ElementRead, status_code=status.HTTP_201_CREATED)
def create_element(db: DbDep, payload: ElementCreate, principal=Depends(require_role("editor"))):
    return catalog.create_element(db, principal, payload)


@router.patch("/{slug}", response_model=ElementRead)
def update_element(db: DbDep, slug: str, payload: ElementUpdate, principal=Depends(require_role("editor"))):
    return catalog.update_element(db, principal, slug, payload)


@router.patch("/{slug}/folder", response_model=ElementRead)
def set_folder(db: DbDep, slug: str, body: FolderAssign, principal=Depends(require_role("editor"))):
    return catalog.set_element_folder(db, principal, slug, body.folder_id)


@router.patch("/{slug}/fields", response_model=ElementRead)
def set_fields(db: DbDep, slug: str, body: FieldValues, principal=Depends(require_role("editor"))):
    return catalog.set_element_fields(db, principal, slug, body.values)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_element(db: DbDep, slug: str, principal=Depends(require_role("editor"))):
    catalog.delete_element(db, principal, slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

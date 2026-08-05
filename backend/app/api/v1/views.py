"""View endpoints incl. versioning + semantic diff (SPEC §7, §11)."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Query, Response, status

from ...core.deps import DbDep, PrincipalDep, require_role
from ...schemas.api import (
    ApprovalRead,
    FolderAssign,
    LayoutPut,
    SubmitReviewBody,
    ViewCreate,
    ViewGraphRead,
    ViewRead,
    ViewUpdate,
    VersionRead,
)
from ...services import approvals, views
from ...services.dsl.diff import ModelDiff

router = APIRouter(prefix="/views", tags=["views"])


@router.get("", response_model=list[ViewRead])
def list_views(db: DbDep, principal: PrincipalDep):
    return views.list_views(db, principal.tenant_id)


@router.get("/{slug}", response_model=ViewRead)
def get_view(db: DbDep, principal: PrincipalDep, slug: str):
    return views.get_view(db, principal.tenant_id, slug)


@router.post("", response_model=ViewRead, status_code=status.HTTP_201_CREATED)
def create_view(db: DbDep, payload: ViewCreate, principal=Depends(require_role("editor"))):
    return views.create_view(db, principal, payload)


@router.patch("/{slug}", response_model=ViewRead)
def update_view(db: DbDep, slug: str, payload: ViewUpdate, principal=Depends(require_role("editor"))):
    return views.update_view(db, principal, slug, payload)


@router.patch("/{slug}/folder", response_model=ViewRead)
def set_folder(db: DbDep, slug: str, body: FolderAssign, principal=Depends(require_role("editor"))):
    return views.set_view_folder(db, principal, slug, body.folder_id)


@router.get("/{slug}/render", response_class=Response)
def render_view(db: DbDep, principal: PrincipalDep, slug: str) -> Response:
    svg = views.render_view(db, principal.tenant_id, slug)
    return Response(content=svg, media_type="image/svg+xml")


@router.get("/{slug}/graph", response_model=ViewGraphRead)
def get_view_graph(db: DbDep, principal: PrincipalDep, slug: str):
    """Resolved elements + relations + layout — the canvas load endpoint."""
    return views.get_view_graph(db, principal.tenant_id, slug)


@router.put("/{slug}/layout", status_code=status.HTTP_204_NO_CONTENT)
def put_layout(db: DbDep, slug: str, payload: LayoutPut, principal=Depends(require_role("editor"))):
    views.put_layout(db, principal, slug, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{slug}/versions", response_model=VersionRead, status_code=status.HTTP_201_CREATED)
def create_version(db: DbDep, slug: str, message: str | None = Body(None, embed=True), principal=Depends(require_role("editor"))):
    return views.create_view_version(db, principal, slug, message)


@router.get("/{slug}/versions", response_model=list[VersionRead])
def list_versions(db: DbDep, principal: PrincipalDep, slug: str):
    return views.list_view_versions(db, principal.tenant_id, slug)


@router.post("/{slug}/submit-review", response_model=ApprovalRead, status_code=status.HTTP_201_CREATED)
def submit_review(db: DbDep, slug: str, body: SubmitReviewBody, principal=Depends(require_role("editor"))):
    return approvals.submit_review(db, principal, slug, body.approvers, body.comment)


@router.post("/{slug}/publish", response_model=ViewRead)
def publish(db: DbDep, slug: str, principal=Depends(require_role("approver"))):
    return approvals.publish(db, principal, slug)


@router.post("/{slug}/deprecate", response_model=ViewRead)
def deprecate(db: DbDep, slug: str, principal=Depends(require_role("approver"))):
    return approvals.deprecate(db, principal, slug)


@router.get("/{slug}/diff", response_model=ModelDiff)
def diff_versions(
    db: DbDep,
    principal: PrincipalDep,
    slug: str,
    from_: int = Query(alias="from"),
    to: int = Query(...),
):
    return views.diff_view_versions(db, principal.tenant_id, slug, from_, to)

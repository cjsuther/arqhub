"""View comment endpoints (SPEC §11)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from ...core.deps import DbDep, PrincipalDep, require_role
from ...schemas.api import CommentCreate, CommentRead
from ...services import comments

router = APIRouter(tags=["comments"])


@router.get("/views/{slug}/comments", response_model=list[CommentRead])
def list_comments(db: DbDep, principal: PrincipalDep, slug: str):
    return comments.list_comments(db, principal.tenant_id, slug)


@router.post("/views/{slug}/comments", response_model=CommentRead, status_code=status.HTTP_201_CREATED)
def add_comment(db: DbDep, slug: str, body: CommentCreate, principal=Depends(require_role("viewer"))):
    return comments.create_comment(db, principal, slug, body.body)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(db: DbDep, comment_id: str, principal=Depends(require_role("viewer"))):
    comments.delete_comment(db, principal, comment_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

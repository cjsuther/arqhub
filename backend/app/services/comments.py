"""View comments — lightweight collaboration thread (SPEC §11)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select

from ..core.auth import Principal
from ..core.deps import write_audit
from ..models import Comment, User
from ..schemas.api import CommentRead
from . import views as views_service


def _to_read(names: dict[str, str], c: Comment) -> CommentRead:
    return CommentRead(
        id=c.id,
        body=c.body,
        author_id=c.author_id,
        author_name=names.get(c.author_id or "", "—"),
        created_at=c.created_at.isoformat() if c.created_at else "",
    )


def list_comments(db, tenant_id: str, slug: str) -> list[CommentRead]:
    view = views_service._get_view_row(db, tenant_id, slug)
    rows = db.scalars(
        select(Comment).where(Comment.tenant_id == tenant_id, Comment.view_id == view.id)
        .order_by(Comment.created_at)
    ).all()
    names = {u.id: u.display_name for u in db.scalars(select(User).where(User.tenant_id == tenant_id)).all()}
    return [_to_read(names, c) for c in rows]


def create_comment(db, principal: Principal, slug: str, body: str, mentions: list[str] | None = None) -> CommentRead:
    from .notifications import get_notifier, store

    view = views_service._get_view_row(db, principal.tenant_id, slug)
    text = (body or "").strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El comentario no puede estar vacío.")
    c = Comment(tenant_id=principal.tenant_id, view_id=view.id, author_id=principal.user_id, body=text)
    db.add(c)
    write_audit(db, principal, action="comment", entity="view", entity_id=slug,
                payload={"mentions": mentions or []})
    db.commit()
    db.refresh(c)
    names = {u.id: u.display_name for u in db.scalars(select(User).where(User.tenant_id == principal.tenant_id)).all()}

    # Notify mentioned users (excluding the author).
    mentioned_ids = [uid for uid in (mentions or []) if uid in names and uid != principal.user_id]
    if mentioned_ids:
        get_notifier().comment_mention(
            view_slug=slug, view_name=view.name,
            comment_by=names.get(principal.user_id, principal.email),
            mentioned=[names[uid] for uid in mentioned_ids], body=text,
        )
        store.record(
            db, principal.tenant_id, mentioned_ids,
            kind="comment_mention", title=f"Te mencionaron en {view.name}",
            body=text, view_slug=slug,
        )
    return _to_read(names, c)


def delete_comment(db, principal: Principal, comment_id: str) -> None:
    c = db.get(Comment, comment_id)
    if c is None or c.tenant_id != principal.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Comentario no encontrado.")
    # Author or admin may delete.
    if c.author_id != principal.user_id and principal.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el autor o un admin puede borrar el comentario.")
    db.delete(c)
    write_audit(db, principal, action="delete_comment", entity="view")
    db.commit()

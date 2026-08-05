"""Visibility rules (SPEC §12): group-based folder access + draft privacy.

Model (opt-in): a folder with no group grants is public; once any group is
granted, only members of those groups (and admins) can see it — and, by
containment, its descendants. Items with no folder are always visible. A draft
view is private to its author plus explicit shares (admins bypass everything).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.auth import Principal
from ..models import Folder, GroupFolder, UserGroup, View, ViewShare


def user_group_ids(db: Session, tenant_id: str, user_id: str | None) -> set[str]:
    if not user_id:
        return set()
    return set(
        db.scalars(
            select(UserGroup.group_id).where(
                UserGroup.tenant_id == tenant_id, UserGroup.user_id == user_id
            )
        ).all()
    )


def accessible_folder_ids(db: Session, principal: Principal) -> set[str] | None:
    """Folder ids the principal may see. ``None`` means "all" (admin bypass)."""
    if principal.role == "admin":
        return None

    folders = db.scalars(select(Folder).where(Folder.tenant_id == principal.tenant_id)).all()
    grants = db.scalars(select(GroupFolder).where(GroupFolder.tenant_id == principal.tenant_id)).all()

    granted_groups: dict[str, set[str]] = {}
    for g in grants:
        granted_groups.setdefault(g.folder_id, set()).add(g.group_id)
    mine = user_group_ids(db, principal.tenant_id, principal.user_id)
    parent = {f.id: f.parent_id for f in folders}

    def folder_ok(fid: str) -> bool:
        gs = granted_groups.get(fid)
        return not gs or bool(gs & mine)  # public, or user is in a granted group

    def accessible(fid: str) -> bool:
        cur: str | None = fid
        seen: set[str] = set()
        while cur and cur not in seen:  # walk up the chain (containment)
            seen.add(cur)
            if not folder_ok(cur):
                return False
            cur = parent.get(cur)
        return True

    return {f.id for f in folders if accessible(f.id)}


def folder_visible(accessible: set[str] | None, folder_id: str | None) -> bool:
    return accessible is None or folder_id is None or folder_id in accessible


def view_shares(db: Session, tenant_id: str) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for s in db.scalars(select(ViewShare).where(ViewShare.tenant_id == tenant_id)).all():
        out.setdefault(s.view_id, set()).add(s.user_id)
    return out


def can_see_view(
    principal: Principal, view: View, accessible: set[str] | None, shares: set[str]
) -> bool:
    if principal.role == "admin":
        return True
    # A draft is private to its author + explicit shares (legacy null author = public).
    if view.status == "draft" and view.created_by:
        if principal.user_id != view.created_by and principal.user_id not in shares:
            return False
    return folder_visible(accessible, view.folder_id)

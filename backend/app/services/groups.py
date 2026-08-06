"""Groups + folder visibility grants + membership (SPEC §12)."""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..core.auth import Principal
from ..core.deps import write_audit
from ..models import Folder, Group, GroupFolder, User, UserGroup
from ..schemas.api import GroupCreate, GroupRead, GroupRef, GroupUpdate


def _read(db: Session, tenant_id: str, g: Group) -> GroupRead:
    user_ids = list(db.scalars(select(UserGroup.user_id).where(UserGroup.group_id == g.id)).all())
    folder_ids = db.scalars(select(GroupFolder.folder_id).where(GroupFolder.group_id == g.id)).all()
    return GroupRead(
        id=g.id, name=g.name, member_count=len(user_ids),
        folder_ids=list(folder_ids), user_ids=user_ids,
    )


def list_groups(db: Session, tenant_id: str) -> list[GroupRead]:
    rows = db.scalars(select(Group).where(Group.tenant_id == tenant_id).order_by(Group.name)).all()
    return [_read(db, tenant_id, g) for g in rows]


def groups_of_user(db: Session, tenant_id: str, user_id: str) -> list[GroupRef]:
    rows = db.scalars(
        select(Group)
        .join(UserGroup, UserGroup.group_id == Group.id)
        .where(UserGroup.tenant_id == tenant_id, UserGroup.user_id == user_id)
        .order_by(Group.name)
    ).all()
    return [GroupRef(id=g.id, name=g.name) for g in rows]


def _get(db: Session, tenant_id: str, group_id: str) -> Group:
    g = db.get(Group, group_id)
    if g is None or g.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Grupo no encontrado.")
    return g


def create_group(db: Session, principal: Principal, payload: GroupCreate) -> GroupRead:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El nombre del grupo es obligatorio.")
    g = Group(tenant_id=principal.tenant_id, name=name)
    db.add(g)
    write_audit(db, principal, action="create", entity="group", entity_id=name)
    db.commit()
    db.refresh(g)
    return _read(db, principal.tenant_id, g)


def update_group(db: Session, principal: Principal, group_id: str, payload: GroupUpdate) -> GroupRead:
    g = _get(db, principal.tenant_id, group_id)
    if payload.name is not None and payload.name.strip():
        g.name = payload.name.strip()
    write_audit(db, principal, action="update", entity="group", entity_id=g.name)
    db.commit()
    return _read(db, principal.tenant_id, g)


def delete_group(db: Session, principal: Principal, group_id: str) -> None:
    g = _get(db, principal.tenant_id, group_id)
    db.execute(delete(UserGroup).where(UserGroup.group_id == g.id))
    db.execute(delete(GroupFolder).where(GroupFolder.group_id == g.id))
    db.delete(g)
    write_audit(db, principal, action="delete", entity="group", entity_id=g.name)
    db.commit()


def set_user_groups(db: Session, principal: Principal, user_id: str, group_ids: list[str]) -> None:
    user = db.get(User, user_id)
    if user is None or user.tenant_id != principal.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado.")
    valid = set(db.scalars(select(Group.id).where(Group.tenant_id == principal.tenant_id)).all())
    db.execute(delete(UserGroup).where(UserGroup.user_id == user_id))
    for gid in dict.fromkeys(group_ids):  # de-dup, keep order
        if gid in valid:
            db.add(UserGroup(tenant_id=principal.tenant_id, user_id=user_id, group_id=gid))
    write_audit(db, principal, action="set_groups", entity="user", entity_id=user.email,
                payload={"groups": group_ids})
    db.commit()


def set_group_members(db: Session, principal: Principal, group_id: str, user_ids: list[str]) -> GroupRead:
    g = _get(db, principal.tenant_id, group_id)
    valid = set(db.scalars(select(User.id).where(User.tenant_id == principal.tenant_id)).all())
    db.execute(delete(UserGroup).where(UserGroup.group_id == group_id))
    for uid in dict.fromkeys(user_ids):
        if uid in valid:
            db.add(UserGroup(tenant_id=principal.tenant_id, user_id=uid, group_id=group_id))
    write_audit(db, principal, action="set_members", entity="group", entity_id=g.name,
                payload={"users": user_ids})
    db.commit()
    return _read(db, principal.tenant_id, g)


def get_folder_groups(db: Session, tenant_id: str, folder_id: str) -> list[str]:
    return list(db.scalars(select(GroupFolder.group_id).where(GroupFolder.folder_id == folder_id)).all())


def set_folder_groups(db: Session, principal: Principal, folder_id: str, group_ids: list[str]) -> list[str]:
    folder = db.get(Folder, folder_id)
    if folder is None or folder.tenant_id != principal.tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Carpeta no encontrada.")
    valid = set(db.scalars(select(Group.id).where(Group.tenant_id == principal.tenant_id)).all())
    db.execute(delete(GroupFolder).where(GroupFolder.folder_id == folder_id))
    for gid in dict.fromkeys(group_ids):
        if gid in valid:
            db.add(GroupFolder(tenant_id=principal.tenant_id, group_id=gid, folder_id=folder_id))
    write_audit(db, principal, action="set_visibility", entity="folder", entity_id=folder_id,
                payload={"groups": group_ids})
    db.commit()
    return get_folder_groups(db, principal.tenant_id, folder_id)

"""Approval endpoints (SPEC §7, §11)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ...core.deps import DbDep, PrincipalDep, require_role
from ...schemas.api import ApprovalRead, ResolveBody
from ...services import approvals

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("", response_model=list[ApprovalRead])
def list_approvals(
    db: DbDep, principal: PrincipalDep, status: str | None = None, mine: bool = False
):
    return approvals.list_approvals(db, principal, status_filter=status, mine=mine)


@router.post("/{approval_id}/approve", response_model=ApprovalRead)
def approve(db: DbDep, approval_id: str, body: ResolveBody,
            principal=Depends(require_role("approver"))):
    return approvals.approve(db, principal, approval_id, body.comment)


@router.post("/{approval_id}/reject", response_model=ApprovalRead)
def reject(db: DbDep, approval_id: str, body: ResolveBody,
           principal=Depends(require_role("approver"))):
    return approvals.reject(db, principal, approval_id, body.comment)

"""Governance: state machine + approval workflow (SPEC §11).

    draft --submit-review--> in_review --approve--> (publishable) --publish--> published
      ^                          | reject                                        | deprecate
      +--------------------------+                                               v
                                                                            deprecated

Editing an ``in_review`` view cancels its request and returns it to draft
(handled in ``views.update_view``). Approve/reject/publish require the approver
role; the IA (via MCP) never gets these — it can only submit for review (§9).
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.auth import Principal
from ..core.deps import write_audit
from ..models import ApprovalRequest, View
from ..schemas.api import ApprovalRead, ViewRead
from . import views as views_service
from .notifications import get_notifier


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_read(db: Session, tenant_id: str, ar: ApprovalRequest) -> ApprovalRead:
    view = db.get(View, ar.view_id)
    return ApprovalRead(
        id=ar.id, view_slug=view.slug if view else "?", view_version=ar.view_version,
        status=ar.status, requested_by=ar.requested_by, approvers=list(ar.approvers or []),
        resolved_by=ar.resolved_by, comment=ar.comment,
    )


def submit_review(
    db: Session, principal: Principal, slug: str, approvers: list[str], comment: str | None
) -> ApprovalRead:
    row = views_service._get_view_row(db, principal.tenant_id, slug)
    if row.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only draft views can be submitted for review.")

    version = views_service.create_view_version(
        db, principal, slug, message="submit for review"
    ).version
    row.status = "in_review"
    ar = ApprovalRequest(
        tenant_id=principal.tenant_id, view_id=row.id, view_version=version,
        requested_by=principal.user_id, status="pending", approvers=approvers, comment=comment,
    )
    db.add(ar)
    write_audit(db, principal, action="submit_review", entity="view", entity_id=slug,
                payload={"version": version, "approvers": approvers})
    db.commit()

    get_notifier().approval_requested(
        view_slug=slug, view_name=row.name, requested_by=principal.email,
        approvers=approvers, comment=comment,
    )
    return _to_read(db, principal.tenant_id, ar)


def _get_pending(db: Session, tenant_id: str, approval_id: str) -> ApprovalRequest:
    ar = db.get(ApprovalRequest, approval_id)
    if ar is None or ar.tenant_id != tenant_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approval request not found.")
    if ar.status != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Request already {ar.status}.")
    return ar


def _resolve(db, principal, approval_id, *, outcome: str, comment) -> ApprovalRead:
    ar = _get_pending(db, principal.tenant_id, approval_id)
    ar.status = outcome
    ar.resolved_by = principal.user_id
    ar.resolved_at = _now()
    ar.comment = comment or ar.comment

    view = db.get(View, ar.view_id)
    if outcome == "rejected" and view is not None:
        view.status = "draft"  # back to the editor
    write_audit(db, principal, action=outcome, entity="approval", entity_id=approval_id,
                payload={"view": view.slug if view else None})
    db.commit()

    get_notifier().approval_resolved(
        view_slug=view.slug if view else "?", view_name=view.name if view else "?",
        status=outcome, resolved_by=principal.email, requested_by=ar.requested_by,
    )
    return _to_read(db, principal.tenant_id, ar)


def approve(db, principal, approval_id, comment=None) -> ApprovalRead:
    return _resolve(db, principal, approval_id, outcome="approved", comment=comment)


def reject(db, principal, approval_id, comment=None) -> ApprovalRead:
    return _resolve(db, principal, approval_id, outcome="rejected", comment=comment)


def publish(db, principal, slug) -> ViewRead:
    row = views_service._get_view_row(db, principal.tenant_id, slug)
    approved = db.scalar(
        select(ApprovalRequest).where(
            ApprovalRequest.tenant_id == principal.tenant_id,
            ApprovalRequest.view_id == row.id,
            ApprovalRequest.view_version == row.current_version,
            ApprovalRequest.status == "approved",
        )
    )
    if approved is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Publish requires an approved review of the current version."
        )
    row.status = "published"
    write_audit(db, principal, action="publish", entity="view", entity_id=slug,
                payload={"version": row.current_version})
    db.commit()
    return views_service.get_view(db, principal.tenant_id, slug)


def deprecate(db, principal, slug) -> ViewRead:
    row = views_service._get_view_row(db, principal.tenant_id, slug)
    row.status = "deprecated"
    write_audit(db, principal, action="deprecate", entity="view", entity_id=slug)
    db.commit()
    return views_service.get_view(db, principal.tenant_id, slug)


def list_approvals(db, principal, *, status_filter=None, mine=False) -> list[ApprovalRead]:
    q = select(ApprovalRequest).where(ApprovalRequest.tenant_id == principal.tenant_id)
    if status_filter:
        q = q.where(ApprovalRequest.status == status_filter)
    rows = db.scalars(q.order_by(ApprovalRequest.created_at.desc())).all()
    out = []
    for ar in rows:
        if mine and principal.user_id != ar.requested_by and principal.email not in (ar.approvers or []):
            continue
        out.append(_to_read(db, principal.tenant_id, ar))
    return out

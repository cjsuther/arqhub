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
from ..models import ApprovalDecision, ApprovalRequest, User, View
from ..schemas.api import ApprovalDecisionRead, ApprovalRead, ViewRead
from . import views as views_service
from .notifications import get_notifier


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _name_resolver(db: Session, tenant_id: str):
    """Map a user id (or email) to a display name; identity if unknown."""
    users = db.scalars(select(User).where(User.tenant_id == tenant_id)).all()
    by_id = {u.id: u.display_name for u in users}
    by_email = {u.email: u.display_name for u in users}

    def resolve(ref: str | None) -> str | None:
        if ref is None:
            return None
        return by_id.get(ref) or by_email.get(ref) or ref

    return resolve


def _to_read(db: Session, tenant_id: str, ar: ApprovalRequest) -> ApprovalRead:
    view = db.get(View, ar.view_id)
    name = _name_resolver(db, tenant_id)
    approvers = list(ar.approvers or [])
    decisions = db.scalars(
        select(ApprovalDecision).where(ApprovalDecision.approval_id == ar.id)
        .order_by(ApprovalDecision.created_at)
    ).all()
    return ApprovalRead(
        id=ar.id, view_slug=view.slug if view else "?", view_version=ar.view_version,
        view_status=view.status if view else "?",
        status=ar.status,
        created_at=ar.created_at.isoformat() if ar.created_at else "",
        requested_by=ar.requested_by, requested_by_name=name(ar.requested_by),
        approvers=approvers, approver_names=[name(a) or a for a in approvers],
        decisions=[
            ApprovalDecisionRead(
                approver_id=d.approver_id, approver_name=name(d.approver_id),
                decision=d.decision, comment=d.comment,
                decided_at=d.created_at.isoformat() if d.created_at else "",
            )
            for d in decisions
        ],
        resolved_by=ar.resolved_by, resolved_by_name=name(ar.resolved_by),
        resolved_at=ar.resolved_at.isoformat() if ar.resolved_at else None,
        comment=ar.comment,
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
    views_service.set_view_status(db, row, "in_review", principal)
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


def _approver_ids(db: Session, tenant_id: str, approvers: list[str]) -> set[str]:
    """Resolve the designated approvers (ids or emails) to user ids."""
    users = db.scalars(select(User).where(User.tenant_id == tenant_id)).all()
    by_id = {u.id for u in users}
    by_email = {u.email: u.id for u in users}
    out: set[str] = set()
    for a in approvers:
        if a in by_id:
            out.add(a)
        elif a in by_email:
            out.add(by_email[a])
    return out


def _recompute_status(decisions: list[ApprovalDecision], approver_ids: set[str]) -> str:
    """Overall status from the individual decisions (multi-approver policy §11).

    Any rejection rejects the request; it is approved once every designated
    approver has approved (or, when none was named/resolvable, on the first
    approval); otherwise it stays pending.
    """
    if any(d.decision == "rejected" for d in decisions):
        return "rejected"
    approved = {d.approver_id for d in decisions if d.decision == "approved"}
    if approver_ids:
        return "approved" if approver_ids <= approved else "pending"
    return "approved" if approved else "pending"


def _decide(db, principal, approval_id, *, decision: str, comment) -> ApprovalRead:
    if not comment or not comment.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El comentario es obligatorio al aprobar o rechazar.")
    ar = _get_pending(db, principal.tenant_id, approval_id)

    # Upsert this approver's decision (re-deciding overwrites the previous one).
    existing = db.scalar(
        select(ApprovalDecision).where(
            ApprovalDecision.approval_id == ar.id, ApprovalDecision.approver_id == principal.user_id
        )
    )
    if existing is not None:
        existing.decision = decision
        existing.comment = comment.strip()
    else:
        db.add(ApprovalDecision(
            tenant_id=principal.tenant_id, approval_id=ar.id,
            approver_id=principal.user_id, decision=decision, comment=comment.strip(),
        ))
    db.flush()

    decisions = db.scalars(select(ApprovalDecision).where(ApprovalDecision.approval_id == ar.id)).all()
    if principal.role == "admin":
        # Admin override: an administrator's decision resolves the request outright,
        # regardless of the designated approvers (authority + escape hatch).
        ar.status = "rejected" if decision == "rejected" else "approved"
    else:
        ar.status = _recompute_status(
            decisions, _approver_ids(db, principal.tenant_id, list(ar.approvers or []))
        )

    view = db.get(View, ar.view_id)
    if ar.status in ("approved", "rejected"):
        ar.resolved_by = principal.user_id
        ar.resolved_at = _now()
        ar.comment = comment.strip()
        if ar.status == "rejected" and view is not None:
            views_service.set_view_status(db, view, "draft", principal)  # back to the editor

    write_audit(db, principal, action=decision, entity="approval", entity_id=approval_id,
                payload={"view": view.slug if view else None, "request_status": ar.status})
    db.commit()

    get_notifier().approval_resolved(
        view_slug=view.slug if view else "?", view_name=view.name if view else "?",
        status=decision, resolved_by=principal.email, requested_by=ar.requested_by,
    )
    return _to_read(db, principal.tenant_id, ar)


def approve(db, principal, approval_id, comment=None) -> ApprovalRead:
    return _decide(db, principal, approval_id, decision="approved", comment=comment)


def reject(db, principal, approval_id, comment=None) -> ApprovalRead:
    return _decide(db, principal, approval_id, decision="rejected", comment=comment)


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
    views_service.set_view_status(db, row, "published", principal)
    write_audit(db, principal, action="publish", entity="view", entity_id=slug,
                payload={"version": row.current_version})
    db.commit()
    return views_service.get_view(db, principal.tenant_id, slug)


def deprecate(db, principal, slug) -> ViewRead:
    row = views_service._get_view_row(db, principal.tenant_id, slug)
    views_service.set_view_status(db, row, "deprecated", principal)
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

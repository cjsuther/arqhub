"""Request/response models for the REST API (SPEC §7)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..services.dsl.diff import ModelDiff
from ..services.dsl.registry import Lifecycle
from ..services.dsl.validator import ValidationReport


# --- Elements ----------------------------------------------------------------
class ElementCreate(BaseModel):
    slug: str
    name: str
    kind: str
    domain: str | None = None
    owner: str | None = None
    description: str | None = None
    lifecycle: Lifecycle = Lifecycle.active
    tags: list[str] = Field(default_factory=list)
    properties: dict[str, str] = Field(default_factory=dict)
    mappings: dict[str, str] = Field(default_factory=dict)


class ElementUpdate(BaseModel):
    name: str | None = None
    kind: str | None = None
    domain: str | None = None
    owner: str | None = None
    description: str | None = None
    lifecycle: Lifecycle | None = None
    tags: list[str] | None = None
    properties: dict[str, str] | None = None
    mappings: dict[str, str] | None = None


class ElementRead(BaseModel):
    slug: str
    name: str
    kind: str
    domain: str | None = None
    owner: str | None = None
    description: str | None = None
    lifecycle: str
    tags: list[str]
    properties: dict
    mappings: dict
    folder_id: str | None = None


# --- Relationships -----------------------------------------------------------
class RelationshipCreate(BaseModel):
    slug: str | None = None
    from_: str = Field(alias="from")
    to: str
    kind: str
    label: str | None = None
    properties: dict[str, str] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class RelationshipUpdate(BaseModel):
    label: str | None = None
    properties: dict[str, str] | None = None


class RelationshipRead(BaseModel):
    model_config = {"populate_by_name": True}

    slug: str
    from_: str = Field(alias="from")
    to: str
    kind: str
    label: str | None = None
    properties: dict


# --- Views -------------------------------------------------------------------
class ViewInclude(BaseModel):
    elements: list[str] = Field(default_factory=list)
    relations: list[str] | str = "auto"


class ViewCreate(BaseModel):
    slug: str
    name: str
    lang: str
    viewpoint: str | None = None
    include: ViewInclude = Field(default_factory=ViewInclude)


class ViewUpdate(BaseModel):
    name: str | None = None
    viewpoint: str | None = None
    include: dict | None = None
    status: str | None = None
    notes: str | None = None


class ViewRead(BaseModel):
    slug: str
    name: str
    lang: str
    viewpoint: str | None = None
    include: dict
    status: str
    status_changed_at: str | None = None
    status_changed_by: str | None = None
    status_changed_by_name: str | None = None
    created_by: str | None = None
    created_by_name: str | None = None
    current_version: int
    folder_id: str | None = None
    notes: str | None = None


# --- Comments ----------------------------------------------------------------
class CommentCreate(BaseModel):
    body: str


class CommentRead(BaseModel):
    id: str
    body: str
    author_id: str | None = None
    author_name: str | None = None
    created_at: str


# --- Folders (hierarchical organisation, presentation) -----------------------
class FolderCreate(BaseModel):
    name: str
    scope: str  # element | view
    parent_id: str | None = None


class FolderUpdate(BaseModel):
    name: str | None = None
    parent_id: str | None = None  # move; null = root


class FolderRead(BaseModel):
    id: str
    name: str
    scope: str
    parent_id: str | None = None


class FolderAssign(BaseModel):
    folder_id: str | None = None  # null = move to root/unassigned


class VersionRead(BaseModel):
    version: int
    scope: str
    scope_id: str | None
    message: str | None


# --- Layout (presentation, separate from the model — SPEC §1, §6) ------------
class LayoutNode(BaseModel):
    element: str  # element slug
    x: float
    y: float
    w: float = 0.0
    h: float = 0.0
    parent: str | None = None  # pool/lane element slug this node is nested in
    style: dict = Field(default_factory=dict)


class LayoutPut(BaseModel):
    nodes: list[LayoutNode] = Field(default_factory=list)


class ViewGraphRead(BaseModel):
    """Everything the canvas needs to render/edit a view in one call."""

    view: ViewRead
    elements: list[ElementRead]
    relations: list[RelationshipRead]
    layout: list[LayoutNode]


# --- Users (SPEC §7, §12) ----------------------------------------------------
class GroupRef(BaseModel):
    id: str
    name: str


class UserRead(BaseModel):
    id: str
    email: str
    display_name: str
    role: str  # viewer|editor|approver|admin
    is_entra: bool = False  # provisioned from Entra ID (role re-synced on login)
    groups: list[GroupRef] = []


class UserCreate(BaseModel):
    email: str
    display_name: str
    role: str = "viewer"


class UserUpdate(BaseModel):
    display_name: str | None = None
    role: str | None = None


# --- Groups (folder visibility, SPEC §12) ------------------------------------
class GroupCreate(BaseModel):
    name: str


class GroupUpdate(BaseModel):
    name: str | None = None


class GroupRead(BaseModel):
    id: str
    name: str
    member_count: int = 0
    folder_ids: list[str] = []


class IdList(BaseModel):
    """Generic id-set payload (group assignment, folder grants, draft shares)."""
    ids: list[str] = []


# --- Governance / approvals (SPEC §11) ---------------------------------------
class SubmitReviewBody(BaseModel):
    approvers: list[str] = Field(default_factory=list)  # user emails/ids
    comment: str | None = None


class ResolveBody(BaseModel):
    comment: str = Field(min_length=1)  # mandatory: approve/reject must be justified


class ApprovalDecisionRead(BaseModel):
    approver_id: str | None
    approver_name: str | None
    decision: str  # approved|rejected
    comment: str
    decided_at: str


class ApprovalRead(BaseModel):
    id: str
    view_slug: str
    view_version: int
    view_status: str  # borrador|in_review|published|deprecated of the target view
    status: str  # pending|approved|rejected|cancelled
    created_at: str
    requested_by: str | None  # raw user id (kept for compatibility)
    requested_by_name: str | None  # human-readable name for the UI
    approvers: list[str]
    approver_names: list[str]
    decisions: list[ApprovalDecisionRead] = []
    resolved_by: str | None
    resolved_by_name: str | None
    resolved_at: str | None = None
    comment: str | None


# --- DSL import --------------------------------------------------------------
class ImportReport(BaseModel):
    applied: bool
    dry_run: bool
    validation: ValidationReport
    diff: ModelDiff

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


# --- Relationships -----------------------------------------------------------
class RelationshipCreate(BaseModel):
    slug: str | None = None
    from_: str = Field(alias="from")
    to: str
    kind: str
    label: str | None = None
    properties: dict[str, str] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


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


class ViewRead(BaseModel):
    slug: str
    name: str
    lang: str
    viewpoint: str | None = None
    include: dict
    status: str
    current_version: int


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
    style: dict = Field(default_factory=dict)


class LayoutPut(BaseModel):
    nodes: list[LayoutNode] = Field(default_factory=list)


class ViewGraphRead(BaseModel):
    """Everything the canvas needs to render/edit a view in one call."""

    view: ViewRead
    elements: list[ElementRead]
    relations: list[RelationshipRead]
    layout: list[LayoutNode]


# --- Users (SPEC §7) ---------------------------------------------------------
class UserRead(BaseModel):
    id: str
    email: str
    display_name: str
    role: str  # viewer|editor|approver|admin


# --- Governance / approvals (SPEC §11) ---------------------------------------
class SubmitReviewBody(BaseModel):
    approvers: list[str] = Field(default_factory=list)  # user emails/ids
    comment: str | None = None


class ResolveBody(BaseModel):
    comment: str | None = None


class ApprovalRead(BaseModel):
    id: str
    view_slug: str
    view_version: int
    status: str  # pending|approved|rejected|cancelled
    requested_by: str | None
    approvers: list[str]
    resolved_by: str | None
    comment: str | None


# --- DSL import --------------------------------------------------------------
class ImportReport(BaseModel):
    applied: bool
    dry_run: bool
    validation: ValidationReport
    diff: ModelDiff

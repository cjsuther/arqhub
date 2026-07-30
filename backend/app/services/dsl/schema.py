"""Pydantic models for the arqhub DSL wire format (SPEC §5).

The DSL is the IA-first interchange format: YAML, no coordinates, slug ids. A
document may carry a full ``model``, a set of ``views``, and/or a ``patch`` of
delta operations. These models validate shape only; semantic validation against
the registry lives in ``validator.py``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .registry import Lifecycle

DSL_VERSION = "arqhub/1.0"


class _Base(BaseModel):
    # Reject unknown keys so a malformed DSL fails loudly instead of silently
    # dropping data — LLMs get a precise error to self-correct from.
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ElementDef(_Base):
    name: str
    kind: str
    domain: str | None = None
    owner: str | None = None
    description: str | None = None
    lifecycle: Lifecycle = Lifecycle.active
    tags: list[str] = Field(default_factory=list)
    properties: dict[str, str] = Field(default_factory=dict)
    # Per-language overrides of the registry default projection (SPEC §4.1).
    mappings: dict[str, str] = Field(default_factory=dict)


class RelationDef(_Base):
    id: str | None = None
    from_: str = Field(alias="from")
    to: str
    kind: str
    label: str | None = None
    properties: dict[str, str] = Field(default_factory=dict)


class ViewInclude(_Base):
    elements: list[str] = Field(default_factory=list)
    # Explicit relation-id list, or the literal "auto" (relations between the
    # included elements are pulled in automatically).
    relations: list[str] | str = "auto"


class ViewDef(_Base):
    id: str
    name: str
    lang: str
    viewpoint: str | None = None
    include: ViewInclude = Field(default_factory=ViewInclude)


class ModelSection(_Base):
    elements: dict[str, ElementDef] = Field(default_factory=dict)
    relations: list[RelationDef] = Field(default_factory=list)


class PatchSection(_Base):
    add_elements: dict[str, ElementDef] = Field(default_factory=dict)
    add_relations: list[RelationDef] = Field(default_factory=list)
    update_elements: dict[str, dict] = Field(default_factory=dict)
    update_relations: dict[str, dict] = Field(default_factory=dict)
    remove_elements: list[str] = Field(default_factory=list)
    remove_relations: list[str] = Field(default_factory=list)


class DslDocument(_Base):
    dsl: str = DSL_VERSION
    model: ModelSection | None = None
    views: list[ViewDef] | None = None
    patch: PatchSection | None = None

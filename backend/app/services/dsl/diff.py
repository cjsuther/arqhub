"""Semantic diff between two ModelGraphs (SPEC §6 / §11).

Structural, not textual: compares elements by slug, relations by id and views by
id, reporting what was added, removed or modified. This is the payload behind
``/views/{slug}/diff`` and the version-comparison panel.
"""

from __future__ import annotations

from pydantic import BaseModel

from .graph import ModelGraph


class FieldChange(BaseModel):
    field: str
    before: object | None = None
    after: object | None = None


class ModifiedEntry(BaseModel):
    id: str
    changes: list[FieldChange]


class EntityDiff(BaseModel):
    added: list[str] = []
    removed: list[str] = []
    modified: list[ModifiedEntry] = []

    @property
    def empty(self) -> bool:
        return not (self.added or self.removed or self.modified)


class ModelDiff(BaseModel):
    elements: EntityDiff = EntityDiff()
    relations: EntityDiff = EntityDiff()
    views: EntityDiff = EntityDiff()

    @property
    def empty(self) -> bool:
        return self.elements.empty and self.relations.empty and self.views.empty


def _field_changes(before: dict, after: dict, ignore: set[str]) -> list[FieldChange]:
    changes: list[FieldChange] = []
    for field in sorted(set(before) | set(after)):
        if field in ignore:
            continue
        b, a = before.get(field), after.get(field)
        if b != a:
            changes.append(FieldChange(field=field, before=b, after=a))
    return changes


def _diff_maps(before: dict, after: dict, ignore: set[str]) -> EntityDiff:
    before_keys, after_keys = set(before), set(after)
    entry = EntityDiff(
        added=sorted(after_keys - before_keys),
        removed=sorted(before_keys - after_keys),
    )
    for key in sorted(before_keys & after_keys):
        b = before[key].model_dump(mode="json")
        a = after[key].model_dump(mode="json")
        changes = _field_changes(b, a, ignore)
        if changes:
            entry.modified.append(ModifiedEntry(id=key, changes=changes))
    return entry


def diff_graphs(before: ModelGraph, after: ModelGraph) -> ModelDiff:
    return ModelDiff(
        elements=_diff_maps(before.elements, after.elements, ignore={"slug"}),
        relations=_diff_maps(before.relations, after.relations, ignore={"id"}),
        views=_diff_maps(before.views, after.views, ignore=set()),
    )

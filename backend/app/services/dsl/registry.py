"""Canonical metamodel registry — the single source of truth (SPEC §4.2 / §15).

Everything that maps a canonical ``kind`` or ``relation`` to its per-language
projection lives here. The DSL validator, the exporters and the ``/meta/registry``
endpoint all read from this module; nothing else defines these mappings.

Design notes
------------
* ``kind`` and ``relation`` names are the stable, LLM-friendly tokens used in the
  DSL. Human labels stay in the frontend.
* A per-language projection of ``None`` means the concept does not exist in that
  language (e.g. an ArchiMate ``capability`` has no BPMN counterpart).
* Relation aliases (``uses`` -> ``serving``, ``flow`` -> ``triggering``) are
  accepted on input and normalised to the canonical token.
"""

from __future__ import annotations

from enum import Enum


class Lang(str, Enum):
    archimate = "archimate"
    bpmn = "bpmn"
    uml = "uml"


class Lifecycle(str, Enum):
    proposed = "proposed"
    active = "active"
    deprecated = "deprecated"
    retired = "retired"


# --- Canonical kinds -> per-language concrete type (SPEC §4.2 table) ----------
# A value of None means "not projected in this language".
KIND_MAPPINGS: dict[str, dict[Lang, str | None]] = {
    "actor": {Lang.archimate: "BusinessActor", Lang.uml: "Actor", Lang.bpmn: "Participant"},
    "role": {Lang.archimate: "BusinessRole", Lang.uml: "Actor", Lang.bpmn: "Lane"},
    "process": {Lang.archimate: "BusinessProcess", Lang.uml: "Activity", Lang.bpmn: "Process"},
    "task": {Lang.archimate: "BusinessProcess", Lang.uml: "Action", Lang.bpmn: "Task"},
    "event": {Lang.archimate: "BusinessEvent", Lang.uml: "Signal", Lang.bpmn: "Event"},
    "gateway": {Lang.archimate: "Junction", Lang.uml: "DecisionNode", Lang.bpmn: "Gateway"},
    "service": {Lang.archimate: "ApplicationService", Lang.uml: "Interface", Lang.bpmn: None},
    "app-component": {Lang.archimate: "ApplicationComponent", Lang.uml: "Component", Lang.bpmn: "Participant"},
    "interface": {Lang.archimate: "ApplicationInterface", Lang.uml: "Interface", Lang.bpmn: None},
    "data-object": {Lang.archimate: "DataObject", Lang.uml: "Class", Lang.bpmn: "DataObject"},
    "node": {Lang.archimate: "Node", Lang.uml: "Node", Lang.bpmn: None},
    "artifact": {Lang.archimate: "Artifact", Lang.uml: "Artifact", Lang.bpmn: None},
    "capability": {Lang.archimate: "Capability", Lang.uml: None, Lang.bpmn: None},
    "goal": {Lang.archimate: "Goal", Lang.uml: None, Lang.bpmn: None},
}

# ArchiMate layer per kind — drives node colour in the canvas (SPEC §8.2).
KIND_LAYER: dict[str, str] = {
    "actor": "business",
    "role": "business",
    "process": "business",
    "task": "business",
    "event": "business",
    "gateway": "business",
    "service": "application",
    "app-component": "application",
    "interface": "application",
    "data-object": "application",
    "node": "technology",
    "artifact": "technology",
    "capability": "motivation",
    "goal": "motivation",
}

# --- Canonical relations -> per-language concrete type (SPEC §4.2) -------------
RELATION_MAPPINGS: dict[str, dict[Lang, str | None]] = {
    "composition": {Lang.archimate: "Composition", Lang.uml: "composition", Lang.bpmn: None},
    "aggregation": {Lang.archimate: "Aggregation", Lang.uml: "aggregation", Lang.bpmn: None},
    "assignment": {Lang.archimate: "Assignment", Lang.uml: "association", Lang.bpmn: None},
    "realization": {Lang.archimate: "Realization", Lang.uml: "realization", Lang.bpmn: None},
    "serving": {Lang.archimate: "Serving", Lang.uml: "dependency", Lang.bpmn: "messageFlow"},
    "access": {Lang.archimate: "Access", Lang.uml: "dependency", Lang.bpmn: "dataAssociation"},
    "triggering": {Lang.archimate: "Triggering", Lang.uml: "controlFlow", Lang.bpmn: "sequenceFlow"},
    "association": {Lang.archimate: "Association", Lang.uml: "association", Lang.bpmn: "association"},
    "specialization": {Lang.archimate: "Specialization", Lang.uml: "generalization", Lang.bpmn: None},
    # BPMN-exclusive canonical relations.
    "sequence-flow": {Lang.archimate: None, Lang.uml: "controlFlow", Lang.bpmn: "sequenceFlow"},
    "message-flow": {Lang.archimate: None, Lang.uml: None, Lang.bpmn: "messageFlow"},
}

# Friendly aliases accepted on input, normalised to the canonical token.
RELATION_ALIASES: dict[str, str] = {
    "uses": "serving",
    "flow": "triggering",
}

VALID_KINDS: frozenset[str] = frozenset(KIND_MAPPINGS)
VALID_RELATIONS: frozenset[str] = frozenset(RELATION_MAPPINGS)

# Kinds registered at runtime (persisted in ``custom_kinds``), on top of the
# built-in matrix. The registry stays the single source of truth (SPEC §4.2);
# these just extend it so teams can map components not covered out of the box.
CUSTOM_KINDS: set[str] = set()


def register_kind(key: str, layer: str, mappings: dict[Lang, str | None], *, custom: bool = True) -> None:
    """Add/replace a kind and its per-language projection in the live registry."""
    KIND_MAPPINGS[key] = {lang: mappings.get(lang) for lang in Lang}
    KIND_LAYER[key] = layer
    if custom:
        CUSTOM_KINDS.add(key)


def unregister_kind(key: str) -> bool:
    """Remove a custom kind (built-ins can't be removed)."""
    if key not in CUSTOM_KINDS:
        return False
    KIND_MAPPINGS.pop(key, None)
    KIND_LAYER.pop(key, None)
    CUSTOM_KINDS.discard(key)
    return True


def is_valid_kind(kind: str) -> bool:
    return kind in KIND_MAPPINGS


def normalize_relation(kind: str) -> str:
    """Resolve a relation alias to its canonical token (identity if none)."""
    return RELATION_ALIASES.get(kind, kind)


def kind_projection(kind: str, lang: Lang) -> str | None:
    """Concrete type for ``kind`` in ``lang`` (None if not projected)."""
    return KIND_MAPPINGS.get(kind, {}).get(lang)


def relation_projection(relation: str, lang: Lang) -> str | None:
    """Concrete type for a (canonical) relation in ``lang`` (None if absent)."""
    return RELATION_MAPPINGS.get(normalize_relation(relation), {}).get(lang)


def kind_exists_in(kind: str, lang: Lang) -> bool:
    return kind_projection(kind, lang) is not None


def relation_exists_in(relation: str, lang: Lang) -> bool:
    return relation_projection(relation, lang) is not None


def registry_snapshot() -> dict:
    """Serialisable view of the whole registry for the ``/meta/registry`` endpoint."""
    return {
        "langs": [l.value for l in Lang],
        "lifecycles": [l.value for l in Lifecycle],
        "kinds": {
            kind: {
                "layer": KIND_LAYER.get(kind, "application"),
                "mappings": {lang.value: proj for lang, proj in projs.items()},
                "custom": kind in CUSTOM_KINDS,
            }
            for kind, projs in KIND_MAPPINGS.items()
        },
        "relations": {
            rel: {lang.value: proj for lang, proj in projs.items()}
            for rel, projs in RELATION_MAPPINGS.items()
        },
        "relation_aliases": dict(RELATION_ALIASES),
    }

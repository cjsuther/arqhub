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
# A value of None (or an absent language key) means "not projected in that
# language". The 14 "generic" kinds below map across all three languages; the
# rest (built from the lists that follow) are language-specific components.
_GENERIC: dict[str, tuple[str, dict[Lang, str | None]]] = {
    # key: (layer, {lang: concrete type})
    "actor": ("business", {Lang.archimate: "BusinessActor", Lang.uml: "Actor", Lang.bpmn: "Participant"}),
    "role": ("business", {Lang.archimate: "BusinessRole", Lang.uml: "Actor", Lang.bpmn: "Lane"}),
    "process": ("business", {Lang.archimate: "BusinessProcess", Lang.uml: "Activity", Lang.bpmn: "Process"}),
    "task": ("business", {Lang.archimate: "BusinessProcess", Lang.uml: "Action", Lang.bpmn: "Task"}),
    "event": ("business", {Lang.archimate: "BusinessEvent", Lang.uml: "Signal", Lang.bpmn: "Event"}),
    "gateway": ("business", {Lang.archimate: "Junction", Lang.uml: "DecisionNode", Lang.bpmn: "Gateway"}),
    "service": ("application", {Lang.archimate: "ApplicationService", Lang.uml: "Interface", Lang.bpmn: None}),
    "app-component": ("application", {Lang.archimate: "ApplicationComponent", Lang.uml: "Component", Lang.bpmn: "Participant"}),
    "interface": ("application", {Lang.archimate: "ApplicationInterface", Lang.uml: "Interface", Lang.bpmn: None}),
    "data-object": ("application", {Lang.archimate: "DataObject", Lang.uml: "Class", Lang.bpmn: "DataObject"}),
    "node": ("technology", {Lang.archimate: "Node", Lang.uml: "Node", Lang.bpmn: None}),
    "artifact": ("technology", {Lang.archimate: "Artifact", Lang.uml: "Artifact", Lang.bpmn: None}),
    "capability": ("strategy", {Lang.archimate: "Capability", Lang.uml: None, Lang.bpmn: None}),
    "goal": ("motivation", {Lang.archimate: "Goal", Lang.uml: None, Lang.bpmn: None}),
}

# ArchiMate 3.x elements (ArchiMate-only), by layer. Elements already covered by
# a generic kind (actor, role, process, event, app-component, interface, service,
# data-object, node, artifact, capability, goal, gateway=Junction) are omitted.
_ARCHIMATE: dict[str, list[tuple[str, str]]] = {
    "strategy": [("resource", "Resource"), ("course-of-action", "CourseOfAction"), ("value-stream", "ValueStream")],
    "business": [
        ("business-collaboration", "BusinessCollaboration"), ("business-interface", "BusinessInterface"),
        ("business-function", "BusinessFunction"), ("business-interaction", "BusinessInteraction"),
        ("business-service", "BusinessService"), ("business-object", "BusinessObject"),
        ("contract", "Contract"), ("representation", "Representation"), ("product", "Product"),
        ("location", "Location"), ("grouping", "Grouping"),  # composite elements
    ],
    "application": [
        ("application-collaboration", "ApplicationCollaboration"), ("application-function", "ApplicationFunction"),
        ("application-interaction", "ApplicationInteraction"), ("application-process", "ApplicationProcess"),
        ("application-event", "ApplicationEvent"),
    ],
    "technology": [
        ("device", "Device"), ("system-software", "SystemSoftware"),
        ("technology-collaboration", "TechnologyCollaboration"), ("technology-interface", "TechnologyInterface"),
        ("path", "Path"), ("communication-network", "CommunicationNetwork"),
        ("technology-function", "TechnologyFunction"), ("technology-process", "TechnologyProcess"),
        ("technology-interaction", "TechnologyInteraction"), ("technology-event", "TechnologyEvent"),
        ("technology-service", "TechnologyService"),
    ],
    "physical": [
        ("equipment", "Equipment"), ("facility", "Facility"),
        ("distribution-network", "DistributionNetwork"), ("material", "Material"),
    ],
    "motivation": [
        ("stakeholder", "Stakeholder"), ("driver", "Driver"), ("assessment", "Assessment"),
        ("outcome", "Outcome"), ("principle", "Principle"), ("requirement", "Requirement"),
        ("constraint", "Constraint"), ("meaning", "Meaning"), ("value", "Value"),
    ],
    "implementation": [
        ("work-package", "WorkPackage"), ("deliverable", "Deliverable"),
        ("implementation-event", "ImplementationEvent"), ("plateau", "Plateau"), ("gap", "Gap"),
    ],
}

# BPMN 2.0 elements (BPMN-only), beyond the generics (Task/Event/Gateway/Process/
# Participant/Lane/DataObject).
_BPMN: list[tuple[str, str]] = [
    ("start-event", "StartEvent"), ("end-event", "EndEvent"),
    ("intermediate-event", "IntermediateCatchEvent"), ("boundary-event", "BoundaryEvent"),
    ("user-task", "UserTask"), ("service-task", "ServiceTask"), ("script-task", "ScriptTask"),
    ("manual-task", "ManualTask"), ("send-task", "SendTask"), ("receive-task", "ReceiveTask"),
    ("business-rule-task", "BusinessRuleTask"), ("subprocess", "SubProcess"), ("call-activity", "CallActivity"),
    ("exclusive-gateway", "ExclusiveGateway"), ("parallel-gateway", "ParallelGateway"),
    ("inclusive-gateway", "InclusiveGateway"), ("event-based-gateway", "EventBasedGateway"),
    ("complex-gateway", "ComplexGateway"), ("data-store", "DataStoreReference"),
    ("text-annotation", "TextAnnotation"), ("bpmn-group", "Group"),
]

# UML 2.5 elements (UML-only), by layer, beyond the generics (Actor/Activity/
# Action/Component/Interface/Class/Node/Artifact/DecisionNode/Signal).
_UML: dict[str, list[tuple[str, str]]] = {
    "business": [
        ("use-case", "UseCase"), ("state", "State"), ("state-machine", "StateMachine"),
        ("lifeline", "Lifeline"), ("initial-node", "InitialNode"), ("final-node", "ActivityFinalNode"),
        ("fork-node", "ForkNode"), ("join-node", "JoinNode"), ("merge-node", "MergeNode"),
    ],
    "application": [
        ("package", "Package"), ("uml-object", "InstanceSpecification"), ("enumeration", "Enumeration"),
        ("data-type", "DataType"), ("port", "Port"), ("collaboration", "Collaboration"),
        ("association-class", "AssociationClass"),
    ],
}


def _build() -> tuple[dict[str, dict[Lang, str | None]], dict[str, str]]:
    kinds: dict[str, dict[Lang, str | None]] = {}
    layers: dict[str, str] = {}
    for key, (layer, mapping) in _GENERIC.items():
        kinds[key] = dict(mapping)
        layers[key] = layer
    for layer, items in _ARCHIMATE.items():
        for key, t in items:
            kinds[key] = {Lang.archimate: t}
            layers[key] = layer.strip()
    for key, t in _BPMN:
        kinds[key] = {Lang.bpmn: t}
        layers[key] = "application" if key == "data-store" else "business"
    for layer, items in _UML.items():
        for key, t in items:
            kinds[key] = {Lang.uml: t}
            layers[key] = layer
    return kinds, layers


KIND_MAPPINGS, KIND_LAYER = _build()

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

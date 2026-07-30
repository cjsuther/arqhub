"""BPMN 2.0 XML exporter with BPMNDI (SPEC §7, Fase 3).

Emits a flat single-process definition with diagram interchange (bounds from the
view layout), valid enough to open in Camunda Modeler. Pools/lanes are a later
refinement; here every BPMN-projectable element becomes a flow node and every
relation between two of them a sequence flow.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from ..dsl.graph import Element, Relation
from ..dsl.registry import Lang, kind_exists_in
from ..dsl.schema import ViewDef

BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
DC = "http://www.omg.org/spec/DD/20100524/DC"
DI = "http://www.omg.org/spec/DD/20100524/DI"

# Canonical kind -> BPMN flow-node tag. Anything else BPMN-projectable -> task.
FLOW_TAG = {
    "task": "task",
    "process": "task",
    "event": "intermediateThrowEvent",
    "gateway": "exclusiveGateway",
}


def _tostring(root: ET.Element) -> str:
    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def _nid(slug: str) -> str:
    return f"Node_{slug}"


def _fid(rid: str) -> str:
    return f"Flow_{rid}"


def export_bpmn(
    elements: list[Element],
    relations: list[Relation],
    view: ViewDef,
    positions: dict[str, tuple[float, float, float, float]],
) -> str:
    for prefix, uri in (("bpmn", BPMN), ("bpmndi", BPMNDI), ("dc", DC), ("di", DI)):
        ET.register_namespace(prefix, uri)

    defs = ET.Element(
        f"{{{BPMN}}}definitions",
        {"id": f"Definitions_{view.id}", "targetNamespace": "http://arqhub/bpmn"},
    )
    process = ET.SubElement(
        defs, f"{{{BPMN}}}process", {"id": f"Process_{view.id}", "isExecutable": "false"}
    )

    nodes = [e for e in elements if kind_exists_in(e.kind, Lang.bpmn)]
    node_slugs = {e.slug for e in nodes}
    flows = [r for r in relations if r.from_ in node_slugs and r.to in node_slugs]

    incoming: dict[str, list[str]] = {e.slug: [] for e in nodes}
    outgoing: dict[str, list[str]] = {e.slug: [] for e in nodes}
    for r in flows:
        outgoing[r.from_].append(_fid(r.id))
        incoming[r.to].append(_fid(r.id))

    for e in nodes:
        tag = FLOW_TAG.get(e.kind, "task")
        el = ET.SubElement(process, f"{{{BPMN}}}{tag}", {"id": _nid(e.slug), "name": e.name})
        for fid in incoming[e.slug]:
            ET.SubElement(el, f"{{{BPMN}}}incoming").text = fid
        for fid in outgoing[e.slug]:
            ET.SubElement(el, f"{{{BPMN}}}outgoing").text = fid

    for r in flows:
        ET.SubElement(
            process, f"{{{BPMN}}}sequenceFlow",
            {"id": _fid(r.id), "sourceRef": _nid(r.from_), "targetRef": _nid(r.to),
             **({"name": r.label} if r.label else {})},
        )

    # --- Diagram interchange ---
    diagram = ET.SubElement(defs, f"{{{BPMNDI}}}BPMNDiagram", {"id": f"Diagram_{view.id}"})
    plane = ET.SubElement(
        diagram, f"{{{BPMNDI}}}BPMNPlane", {"id": f"Plane_{view.id}", "bpmnElement": f"Process_{view.id}"}
    )
    for e in nodes:
        x, y, w, h = positions[e.slug]
        shape = ET.SubElement(
            plane, f"{{{BPMNDI}}}BPMNShape",
            {"id": f"Shape_{e.slug}", "bpmnElement": _nid(e.slug)},
        )
        ET.SubElement(
            shape, f"{{{DC}}}Bounds",
            {"x": str(int(x)), "y": str(int(y)), "width": str(int(w)), "height": str(int(h))},
        )
    for r in flows:
        fx, fy, fw, fh = positions[r.from_]
        tx, ty, tw, th = positions[r.to]
        edge = ET.SubElement(
            plane, f"{{{BPMNDI}}}BPMNEdge",
            {"id": f"Edge_{r.id}", "bpmnElement": _fid(r.id)},
        )
        ET.SubElement(edge, f"{{{DI}}}waypoint", {"x": str(int(fx + fw)), "y": str(int(fy + fh / 2))})
        ET.SubElement(edge, f"{{{DI}}}waypoint", {"x": str(int(tx)), "y": str(int(ty + th / 2))})

    return _tostring(defs)

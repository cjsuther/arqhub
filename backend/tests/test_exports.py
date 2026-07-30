"""Standard-format exporters (SPEC §7, Fase 3): ArchiMate Open Exchange, BPMN 2.0, XMI.

Validates the emitted XML structurally (parses + expected typed nodes)."""

import xml.etree.ElementTree as ET

from app.services.dsl import apply_document, load_dsl
from app.services.exporters import export_archimate, export_bpmn, export_xmi
from tests.conftest import EXAMPLE_DSL

AM = "http://www.opengroup.org/xsd/archimate/3.0/"
BPMN = "http://www.omg.org/spec/BPMN/20100524/MODEL"
BPMNDI = "http://www.omg.org/spec/BPMN/20100524/DI"
UML = "http://schema.omg.org/spec/UML/2.1"
XMI = "http://schema.omg.org/spec/XMI/2.1"


def _graph():
    return apply_document(None, load_dsl(EXAMPLE_DSL)).graph


def _build(graph, view_id):
    view = graph.views[view_id]
    included = [s for s in view.include.elements if s in graph.elements]
    els = [graph.elements[s] for s in included]
    present = set(included)
    rels = [r for r in graph.relations.values() if r.from_ in present and r.to in present]
    positions = {s: (0.0, 0.0, 170.0, 64.0) for s in included}
    return els, rels, view, positions


def test_archimate_open_exchange():
    els, rels, view, pos = _build(_graph(), "vista-app-pagos")
    root = ET.fromstring(export_archimate(els, rels, view, pos))
    assert root.tag == f"{{{AM}}}model"
    elements = root.find(f"{{{AM}}}elements")
    types = {e.get("{http://www.w3.org/2001/XMLSchema-instance}type") for e in elements}
    assert types == {"ApplicationComponent"}
    assert len(elements) == 2
    rel = root.find(f"{{{AM}}}relationships/{{{AM}}}relationship")
    assert rel.get("{http://www.w3.org/2001/XMLSchema-instance}type") == "Serving"
    # The view carries positioned nodes.
    nodes = root.findall(f"{{{AM}}}views/{{{AM}}}diagrams/{{{AM}}}view/{{{AM}}}node")
    assert len(nodes) == 2


def test_bpmn_with_di_opens_flat_process():
    els, rels, view, pos = _build(_graph(), "proceso-originacion")
    xml = export_bpmn(els, rels, view, pos)
    root = ET.fromstring(xml)
    process = root.find(f"{{{BPMN}}}process")
    assert process is not None and process.get("id") == "Process_proceso-originacion"
    tasks = process.findall(f"{{{BPMN}}}task")
    assert len(tasks) == 2  # originacion (process) + api-pagos, both -> task
    flows = process.findall(f"{{{BPMN}}}sequenceFlow")
    assert len(flows) == 1 and flows[0].get("sourceRef") == "Node_originacion"
    # Diagram interchange present (Camunda needs it to render).
    shapes = root.findall(f"{{{BPMNDI}}}BPMNDiagram/{{{BPMNDI}}}BPMNPlane/{{{BPMNDI}}}BPMNShape")
    assert len(shapes) == 2


def test_xmi_uml_model():
    els, rels, view, pos = _build(_graph(), "vista-app-pagos")
    root = ET.fromstring(export_xmi(els, rels, view, pos))
    model = root.find(f"{{{UML}}}Model")
    assert model is not None
    packaged = model.findall("packagedElement")
    types = {p.get(f"{{{XMI}}}type") for p in packaged}
    assert "uml:Component" in types
    assert "uml:Dependency" in types  # serving -> uml dependency

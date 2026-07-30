"""ArchiMate Open Exchange XML exporter (SPEC §7, Fase 3).

Produces The Open Group ArchiMate 3.0 Model Exchange File format, which Archi
imports. Element/relationship concrete types come from the registry projection.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from ..dsl.graph import Element, Relation
from ..dsl.registry import Lang, kind_projection, relation_projection
from ..dsl.schema import ViewDef

NS = "http://www.opengroup.org/xsd/archimate/3.0/"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
XSI_TYPE = f"{{{XSI}}}type"


def _tostring(root: ET.Element) -> str:
    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def export_archimate(
    elements: list[Element],
    relations: list[Relation],
    view: ViewDef,
    positions: dict[str, tuple[float, float, float, float]],
) -> str:
    ET.register_namespace("", NS)
    ET.register_namespace("xsi", XSI)

    model = ET.Element(f"{{{NS}}}model", {"identifier": f"id-{view.id}-model"})
    ET.SubElement(model, f"{{{NS}}}name", {"{http://www.w3.org/XML/1998/namespace}lang": "es"}).text = (
        view.name
    )

    # Only elements/relations that project into ArchiMate are exported.
    els = [e for e in elements if kind_projection(e.kind, Lang.archimate)]
    el_ids = {e.slug for e in els}
    rels = [
        r for r in relations
        if relation_projection(r.kind, Lang.archimate) and r.from_ in el_ids and r.to in el_ids
    ]

    elements_el = ET.SubElement(model, f"{{{NS}}}elements")
    for e in els:
        node = ET.SubElement(
            elements_el, f"{{{NS}}}element",
            {"identifier": f"id-{e.slug}", XSI_TYPE: kind_projection(e.kind, Lang.archimate)},
        )
        ET.SubElement(node, f"{{{NS}}}name").text = e.name
        if e.description:
            ET.SubElement(node, f"{{{NS}}}documentation").text = e.description

    if rels:
        rels_el = ET.SubElement(model, f"{{{NS}}}relationships")
        for r in rels:
            ET.SubElement(
                rels_el, f"{{{NS}}}relationship",
                {
                    "identifier": f"id-{r.id}",
                    "source": f"id-{r.from_}",
                    "target": f"id-{r.to}",
                    XSI_TYPE: relation_projection(r.kind, Lang.archimate),
                },
            )

    views_el = ET.SubElement(model, f"{{{NS}}}views")
    diagrams = ET.SubElement(views_el, f"{{{NS}}}diagrams")
    view_el = ET.SubElement(
        diagrams, f"{{{NS}}}view", {"identifier": f"id-{view.id}", XSI_TYPE: "Diagram"}
    )
    ET.SubElement(view_el, f"{{{NS}}}name").text = view.name

    node_id = {}
    for e in els:
        x, y, w, h = positions[e.slug]
        nid = f"node-{e.slug}"
        node_id[e.slug] = nid
        n = ET.SubElement(
            view_el, f"{{{NS}}}node",
            {
                "identifier": nid, "elementRef": f"id-{e.slug}", XSI_TYPE: "Element",
                "x": str(int(x)), "y": str(int(y)), "w": str(int(w)), "h": str(int(h)),
            },
        )
        ET.SubElement(n, f"{{{NS}}}label").text = e.name
    for r in rels:
        ET.SubElement(
            view_el, f"{{{NS}}}connection",
            {
                "identifier": f"conn-{r.id}", "relationshipRef": f"id-{r.id}",
                XSI_TYPE: "Relationship", "source": node_id[r.from_], "target": node_id[r.to],
            },
        )

    return _tostring(model)

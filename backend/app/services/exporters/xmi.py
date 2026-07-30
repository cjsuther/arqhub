"""XMI (UML 2.5) exporter (SPEC §7, Fase 3).

Emits a UML model with packaged elements typed from the registry's UML
projection and relations as dependencies/realizations. XMI fidelity varies by
tool; this is a correct, importable subset.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from ..dsl.graph import Element, Relation
from ..dsl.registry import Lang, kind_projection, relation_projection
from ..dsl.schema import ViewDef

XMI = "http://schema.omg.org/spec/XMI/2.1"
UML = "http://schema.omg.org/spec/UML/2.1"
XMI_TYPE = f"{{{XMI}}}type"
XMI_ID = f"{{{XMI}}}id"

# UML projection -> XMI packagedElement type for relations (client/supplier form).
_REL_TYPE = {"realization": "uml:Realization"}


def _tostring(root: ET.Element) -> str:
    ET.indent(root)
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


def export_xmi(
    elements: list[Element],
    relations: list[Relation],
    view: ViewDef,
    positions: dict[str, tuple[float, float, float, float]],
) -> str:
    ET.register_namespace("xmi", XMI)
    ET.register_namespace("uml", UML)

    root = ET.Element(f"{{{XMI}}}XMI", {f"{{{XMI}}}version": "2.1"})
    model = ET.SubElement(root, f"{{{UML}}}Model", {XMI_ID: f"model-{view.id}", "name": view.name})

    els = [e for e in elements if kind_projection(e.kind, Lang.uml)]
    el_ids = {e.slug for e in els}
    for e in els:
        ET.SubElement(
            model, "packagedElement",
            {XMI_TYPE: f"uml:{kind_projection(e.kind, Lang.uml)}", XMI_ID: f"id-{e.slug}", "name": e.name},
        )

    for r in relations:
        proj = relation_projection(r.kind, Lang.uml)
        if not proj or r.from_ not in el_ids or r.to not in el_ids:
            continue
        rel_type = _REL_TYPE.get(r.kind, "uml:Dependency")
        ET.SubElement(
            model, "packagedElement",
            {
                XMI_TYPE: rel_type, XMI_ID: f"id-{r.id}",
                **({"name": r.label} if r.label else {}),
                "client": f"id-{r.from_}", "supplier": f"id-{r.to}",
            },
        )

    return _tostring(root)

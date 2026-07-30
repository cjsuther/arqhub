"""Deterministic analysis rules (SPEC §10)."""

from app.services.analysis import analyze
from app.services.dsl.graph import ModelGraph
from app.services.dsl.schema import ElementDef, RelationDef, ViewDef, ViewInclude


def _codes(graph):
    return {f.code for f in analyze(graph)}


def test_detects_possible_duplicate():
    g = ModelGraph()
    g.add_element("api-pagos", ElementDef(name="API de Pagos", kind="app-component"))
    g.add_element("api-pago", ElementDef(name="API de Pago", kind="app-component"))
    # relate them so they are not also orphans-only
    g.add_relation(RelationDef(**{"from": "api-pagos", "to": "api-pago", "kind": "serving"}))
    assert "possible_duplicate" in _codes(g)


def test_detects_orphans():
    g = ModelGraph()
    g.add_element("solo", ElementDef(name="Solo", kind="process"))
    codes = _codes(g)
    assert "orphan_no_relations" in codes and "orphan_no_views" in codes


def test_detects_lifecycle_inconsistency():
    g = ModelGraph()
    g.add_element("a", ElementDef(name="A", kind="app-component", lifecycle="active"))
    g.add_element("b", ElementDef(name="B", kind="app-component", lifecycle="deprecated"))
    g.add_relation(RelationDef(**{"from": "a", "to": "b", "kind": "serving"}))
    findings = [f for f in analyze(g) if f.code == "lifecycle_inconsistency"]
    assert findings and findings[0].entities == ["a", "b"]


def test_detects_high_coupling():
    g = ModelGraph()
    g.add_element("hub", ElementDef(name="Hub", kind="app-component"))
    for i in range(6):
        g.add_element(f"n{i}", ElementDef(name=f"N{i}", kind="app-component"))
        g.add_relation(RelationDef(**{"from": "hub", "to": f"n{i}", "kind": "serving"}))
    assert "high_coupling" in _codes(g)


def test_severity_sorted_first():
    g = ModelGraph()
    g.add_element("a", ElementDef(name="A", kind="app-component", lifecycle="active"))
    g.add_element("b", ElementDef(name="B", kind="app-component", lifecycle="deprecated"))
    g.add_relation(RelationDef(**{"from": "a", "to": "b", "kind": "serving"}))
    g.add_view(ViewDef(id="v", name="V", lang="archimate", include=ViewInclude(elements=["a", "b"])))
    findings = analyze(g)
    severities = [f.severity for f in findings]
    assert severities == sorted(severities, key={"error": 0, "warning": 1, "info": 2}.get)

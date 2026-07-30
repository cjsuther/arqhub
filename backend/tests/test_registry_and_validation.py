"""Registry SSOT (SPEC §4.2) and semantic validation (§5.3) edge cases."""

from app.services.dsl import apply_document, load_dsl, validate_graph
from app.services.dsl.graph import ModelGraph
from app.services.dsl.registry import (
    Lang,
    kind_projection,
    normalize_relation,
    registry_snapshot,
    relation_projection,
)
from app.services.dsl.schema import ElementDef, RelationDef, ViewDef, ViewInclude


def test_kind_projection_per_language():
    assert kind_projection("app-component", Lang.archimate) == "ApplicationComponent"
    assert kind_projection("app-component", Lang.bpmn) == "Participant"
    assert kind_projection("capability", Lang.bpmn) is None  # no BPMN projection


def test_relation_alias_and_projection():
    assert normalize_relation("uses") == "serving"
    assert normalize_relation("flow") == "triggering"
    assert relation_projection("uses", Lang.archimate) == "Serving"
    assert relation_projection("triggering", Lang.bpmn) == "sequenceFlow"


def test_registry_snapshot_is_complete():
    snap = registry_snapshot()
    assert "app-component" in snap["kinds"]
    assert snap["relation_aliases"]["uses"] == "serving"
    assert set(snap["langs"]) == {"archimate", "bpmn", "uml"}


def test_unknown_kind_is_error():
    g = ModelGraph()
    g.add_element("x", ElementDef(name="X", kind="not-a-kind"))
    report = validate_graph(g)
    assert not report.ok
    assert any(i.code == "unknown_kind" for i in report.errors)


def test_dangling_relation_is_error():
    g = ModelGraph()
    g.add_element("a", ElementDef(name="A", kind="process"))
    g.add_relation(RelationDef(**{"from": "a", "to": "ghost", "kind": "serving"}))
    report = validate_graph(g)
    assert any(i.code == "dangling_to" for i in report.errors)


def test_kind_without_lang_projection_is_warning():
    g = ModelGraph()
    g.add_element("cap", ElementDef(name="Cap", kind="capability"))
    g.add_view(
        ViewDef(id="v", name="V", lang="bpmn", include=ViewInclude(elements=["cap"]))
    )
    report = validate_graph(g)
    assert report.ok  # soft: warning, not a hard block
    assert any(i.code == "kind_not_in_lang" for i in report.warnings)


def test_replace_mode_clears_previous_model(example_dsl):
    base = apply_document(None, load_dsl(example_dsl)).graph
    doc = load_dsl(
        "dsl: arqhub/1.0\nmodel:\n  elements:\n    solo:\n      name: Solo\n      kind: process\n"
    )
    replaced = apply_document(base, doc, replace=True).graph
    assert set(replaced.elements) == {"solo"}

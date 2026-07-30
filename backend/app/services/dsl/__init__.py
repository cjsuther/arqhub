"""arqhub DSL engine (SPEC §5): parse, validate, import (model/patch), export, diff.

Pure, DB-agnostic layer operating on ``ModelGraph``. Public surface:
"""

from .diff import ModelDiff, diff_graphs
from .exporter import export_dsl, graph_to_dict
from .graph import Element, ModelGraph, Relation
from .importer import ImportResult, apply_document
from .parser import DslParseError, load_dsl
from .schema import DSL_VERSION, DslDocument
from .validator import ValidationReport, validate_graph

__all__ = [
    "DSL_VERSION",
    "DslDocument",
    "DslParseError",
    "Element",
    "ImportResult",
    "ModelDiff",
    "ModelGraph",
    "Relation",
    "ValidationReport",
    "apply_document",
    "diff_graphs",
    "export_dsl",
    "graph_to_dict",
    "load_dsl",
    "validate_graph",
]

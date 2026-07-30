"""Parse DSL YAML text into a validated ``DslDocument`` (SPEC §5)."""

from __future__ import annotations

import yaml

from .schema import DSL_VERSION, DslDocument


class DslParseError(ValueError):
    """Raised when the YAML is malformed or the document shape is invalid."""


def load_dsl(text: str) -> DslDocument:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as exc:  # pragma: no cover - passthrough of yaml detail
        raise DslParseError(f"Invalid YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise DslParseError("DSL root must be a mapping.")

    version = raw.get("dsl", DSL_VERSION)
    if version != DSL_VERSION:
        raise DslParseError(f"Unsupported DSL version '{version}', expected '{DSL_VERSION}'.")

    try:
        return DslDocument.model_validate(raw)
    except Exception as exc:  # pydantic ValidationError -> friendly wrapper
        raise DslParseError(str(exc)) from exc

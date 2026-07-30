"""Global model snapshots (SPEC §11: daily job + manual).

A snapshot is the whole tenant model exported to the DSL and stored as a
``ModelVersion`` (scope='model'), so the semantic diff can compare any two points
in time.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ModelVersion
from .dsl import graph_to_dict
from .repository import load_graph


def create_model_snapshot(
    db: Session, tenant_id: str, *, message: str | None = None, author_id: str | None = None
) -> ModelVersion:
    """Snapshot the whole model of a tenant as a new ModelVersion."""
    snapshot = graph_to_dict(load_graph(db, tenant_id))

    last = db.scalar(
        select(ModelVersion)
        .where(ModelVersion.tenant_id == tenant_id, ModelVersion.scope == "model")
        .order_by(ModelVersion.version.desc())
    )
    version = (last.version if last else 0) + 1

    row = ModelVersion(
        tenant_id=tenant_id, scope="model", scope_id=None, version=version,
        snapshot=snapshot, message=message or "auto snapshot", author_id=author_id,
    )
    db.add(row)
    db.commit()
    return row

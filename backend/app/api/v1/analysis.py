"""Model analysis endpoint (SPEC §10)."""

from __future__ import annotations

from fastapi import APIRouter

from ...core.deps import DbDep, PrincipalDep
from ...services.analysis import Finding, analyze
from ...services.repository import load_graph

router = APIRouter(tags=["analysis"])


@router.get("/analysis", response_model=list[Finding])
def analyze_model(db: DbDep, principal: PrincipalDep):
    """Run the deterministic optimisation rules over the tenant model."""
    return analyze(load_graph(db, principal.tenant_id))

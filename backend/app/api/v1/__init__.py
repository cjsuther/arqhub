"""API v1 router aggregation (SPEC §7)."""

from fastapi import APIRouter

from . import analysis, approvals, dsl, elements, exports, meta, relationships, views

router = APIRouter()
router.include_router(meta.router)
router.include_router(elements.router)
router.include_router(relationships.router)
router.include_router(views.router)
router.include_router(dsl.router)
router.include_router(exports.router)
router.include_router(approvals.router)
router.include_router(analysis.router)

"""
Router for Source Catalog, Health Checks, and Dynamic Source Management.
Provides:
- GET  /api/sources
- POST /api/sources/{id}/check
- POST /api/sources/{id}/enable
"""

from __future__ import annotations

import logging
from typing import Any, Literal
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.app.config import get_settings
from backend.app.scrapers.adapters import get_adapter
from backend.app.scrapers.health import (
    HealthRecord,
    get_all_source_health,
    get_source_health,
    record_health,
)
from backend.app.scrapers.registry import get_source_spec, load_registry

logger = logging.getLogger("backend.routers.sources")

router = APIRouter(prefix="/api/sources", tags=["sources"])

# In-memory source enable/disable overrides for session
_ENABLED_OVERRIDES: dict[str, bool] = {}


class SourceItemResponse(BaseModel):
    id: str
    label: str
    group: str
    kind: str
    roles: list[str]
    enabled: bool
    status: str
    relevance: str
    tos_risk: str
    requires: str | None = None
    reason: str | None = None
    strategy_used: str | None = None
    last_ok_at: float | None = None
    circuit_breaker_open: bool = False
    ui_visible: bool = False


class EnableSourceRequest(BaseModel):
    enabled: bool


@router.get("", response_model=list[SourceItemResponse])
async def list_sources() -> list[SourceItemResponse]:
    """Returns the full catalog of sources along with their current health and enablement status."""
    registry = load_registry()
    health_map = await get_all_source_health()

    results: list[SourceItemResponse] = []
    for spec in registry.sources:
        # Determine enablement state
        if spec.id in _ENABLED_OVERRIDES:
            is_enabled = _ENABLED_OVERRIDES[spec.id]
        else:
            is_enabled = spec.default_enabled

        # Determine health status
        health = health_map.get(spec.id)
        if spec.status_override:
            status = spec.status_override
            reason = spec.status_reason
            strategy_used = None
            last_ok = None
            is_open = False
        elif health:
            status = health.status
            reason = health.failure_cause
            strategy_used = health.strategy_used
            last_ok = health.last_ok_at
            is_open = health.circuit_breaker_open
        else:
            status = "healthy" if spec.default_enabled else "unknown"
            reason = None
            strategy_used = None
            last_ok = None
            is_open = False

        results.append(
            SourceItemResponse(
                id=spec.id,
                label=spec.label,
                group=spec.group,
                kind=spec.kind,
                roles=[str(r) for r in spec.roles],
                enabled=is_enabled,
                status=status,
                relevance=spec.relevance,
                tos_risk=spec.tos_risk,
                requires=spec.requires,
                reason=reason or spec.notes,
                strategy_used=strategy_used,
                last_ok_at=last_ok,
                circuit_breaker_open=is_open,
                ui_visible=spec.ui_visible,
            )
        )
    return results


@router.post("/{source_id}/check", response_model=HealthRecord)
async def check_source(source_id: str, request: Request) -> HealthRecord:
    """Runs a single-query canary check on a source and records its health."""
    clean_id = source_id.lower().strip()
    spec = get_source_spec(clean_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Source '{clean_id}' not found in registry.")

    if spec.status_override in ("unavailable",):
        return await record_health(
            source_id=clean_id,
            result_status="unavailable",
            status_override="unavailable",
            failure_cause=spec.status_reason,
        )

    adapter = get_adapter(clean_id)
    try:
        res = await adapter.search("black oversized t-shirt men")
        rec = await record_health(
            source_id=clean_id,
            result_status=res.status,
            strategy_used=res.strategy_used,
            failure_cause=res.cause or (res.note if res.status != "ok" else None),
        )
        return rec
    except Exception as e:
        logger.warning(f"Check for {clean_id} raised unexpected exception: {e}")
        return await record_health(
            source_id=clean_id,
            result_status="error",
            failure_cause="timing",
        )


@router.post("/{source_id}/enable")
async def enable_source(source_id: str, req: EnableSourceRequest) -> dict[str, Any]:
    """Enables or disables a source, enforcing risk and availability constraints."""
    clean_id = source_id.lower().strip()
    spec = get_source_spec(clean_id)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Source '{clean_id}' not found in registry.")

    settings = get_settings()

    if req.enabled:
        if spec.status_override in ("unavailable",):
            raise HTTPException(
                status_code=400,
                detail=f"Source '{clean_id}' is unavailable and cannot be enabled: {spec.status_reason}",
            )
        if spec.tos_risk == "high" and not settings.SOURCES_ALLOW_HIGH_RISK:
            raise HTTPException(
                status_code=403,
                detail=f"High risk source '{clean_id}' requires SOURCES_ALLOW_HIGH_RISK=true in backend configuration.",
            )

    _ENABLED_OVERRIDES[clean_id] = req.enabled
    return {"id": clean_id, "enabled": req.enabled}

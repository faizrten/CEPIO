"""Experimental REST adapter for CEPIO Enterprise Performance.

This surface is intentionally outside the stable ``/api/v1`` contract while the
performance capability is qualified. It is an adapter over ``PerformanceService``;
REST does not own performance semantics, contract lifecycle, or workflow authority.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from .auth import ActorContext, get_actor_context
from .performance_registry import (
    PerformanceContractRegistryError,
    RegisteredPerformanceContractResolution,
)
from .performance_runtime import PerformanceObservation
from .performance_service import PerformanceResponseAssessment, PerformanceService


class PerformanceEvaluationRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    observations: tuple[PerformanceObservation, ...]
    evaluated_at: datetime | None = None


def _authorize_scope(actor: ActorContext, organization_id: str | None) -> None:
    if organization_id is None:
        return
    if actor.tenant_id != organization_id:
        raise HTTPException(
            status_code=403,
            detail={
                "code": "performance_organization_scope",
                "message": "Performance contract is outside the authenticated tenant boundary",
            },
        )


def build_performance_router(service: PerformanceService) -> APIRouter:
    router = APIRouter(
        prefix="/experimental/performance/v0.1",
        tags=["performance-experimental"],
    )

    @router.get(
        "/contracts/{contract_id}/resolved",
        response_model=RegisteredPerformanceContractResolution,
    )
    def resolve_performance_contract(
        contract_id: str,
        version: str | None = Query(default=None),
        actor: ActorContext = Depends(get_actor_context),
    ) -> RegisteredPerformanceContractResolution:
        try:
            resolved = service.resolve(contract_id, version)
        except PerformanceContractRegistryError as exc:
            status = 404 if exc.code in {"REVISION_NOT_FOUND", "ACTIVE_REVISION_NOT_FOUND"} else 422
            raise HTTPException(
                status_code=status,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc
        _authorize_scope(actor, resolved.resolved.contract.organization_id)
        return resolved

    @router.post(
        "/contracts/{contract_id}/evaluate",
        response_model=PerformanceResponseAssessment,
    )
    def evaluate_performance_contract(
        contract_id: str,
        body: PerformanceEvaluationRequest,
        version: str | None = Query(default=None),
        actor: ActorContext = Depends(get_actor_context),
    ) -> PerformanceResponseAssessment:
        try:
            resolved = service.resolve(contract_id, version)
        except PerformanceContractRegistryError as exc:
            status = 404 if exc.code in {"REVISION_NOT_FOUND", "ACTIVE_REVISION_NOT_FOUND"} else 422
            raise HTTPException(
                status_code=status,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc
        _authorize_scope(actor, resolved.resolved.contract.organization_id)
        try:
            return service.evaluate(
                contract_id,
                body.observations,
                version=version,
                evaluated_at=body.evaluated_at,
            )
        except (PerformanceContractRegistryError, ValueError) as exc:
            code = getattr(exc, "code", "performance_evaluation")
            raise HTTPException(
                status_code=422,
                detail={"code": code, "message": str(exc)},
            ) from exc

    return router

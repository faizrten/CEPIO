"""Opt-in experimental read-only executive performance preview endpoint.

Not in /api/v1. Request observations are caller supplied and are never
promoted to verified enterprise evidence or persisted as Decisions.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request

from .application_contract import ExecutionContext
from .application_runtime import build_application_service
from .auth import ActorContext, get_actor_context
from .performance_executive import (
    ExecutivePackageRequest,
    ExecutivePerformanceError,
    ExecutivePerformancePackage,
    ExecutivePerformanceService,
)
from .performance_industry_iq import (
    PERFORMANCE_RESPONSE_DECISION_TYPE,
    PERFORMANCE_RESPONSE_IQ_PACK,
    PerformanceIndustryIQService,
    PerformanceReasoningError,
)
from .performance_registry import PerformanceContractRegistryError
from .performance_service import PerformanceService
from .runtime import CEPIORuntime
from .runtime import AuthorizationError


def build_performance_executive_router(service: ExecutivePerformanceService) -> APIRouter:
    router = APIRouter(
        prefix="/experimental/performance/v0.1",
        tags=["performance-executive-experimental"],
    )

    @router.post(
        "/executive/preview",
        response_model=ExecutivePerformancePackage,
        include_in_schema=False,
    )
    def preview_executive_package(
        body: ExecutivePackageRequest,
        request: Request,
        actor: ActorContext = Depends(get_actor_context),
    ) -> ExecutivePerformancePackage:
        # Until server-bound evidence is qualified this surface is administrator-only.
        if "cepio_admin" not in actor.roles:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "executive_preview_admin_required",
                    "message": "Experimental executive preview requires CEPIO administrator role",
                },
            )
        # No caller-supplied actor, roles, tenant or authorization claims.
        context = ExecutionContext(
            actor_id=actor.actor_id,
            actor_roles=frozenset(actor.roles),
            tenant_id=actor.tenant_id,
            correlation_id=getattr(request.state, "request_id", None),
        )
        try:
            return service.preview(body, context)
        except AuthorizationError as exc:
            raise HTTPException(
                status_code=403,
                detail={"code": "performance_unauthorized", "message": str(exc)},
            ) from exc
        except PerformanceReasoningError as exc:
            status = 403 if exc.code == "ORGANIZATION_SCOPE_MISMATCH" else 422
            raise HTTPException(
                status_code=status,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc
        except PerformanceContractRegistryError as exc:
            status = 404 if exc.code in {"REVISION_NOT_FOUND", "ACTIVE_REVISION_NOT_FOUND"} else 422
            raise HTTPException(
                status_code=status,
                detail={"code": exc.code, "message": str(exc)},
            ) from exc
        except (ExecutivePerformanceError, ValueError) as exc:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": getattr(exc, "code", "performance_preview_invalid"),
                    "message": str(exc),
                },
            ) from exc

    return router


def mount_experimental_performance_executive(
    app: FastAPI, runtime: CEPIORuntime, performance_service: PerformanceService
) -> None:
    """Mount only on explicit opt-in, preserving the existing stable public API."""
    if os.getenv("CEPIO_ENABLE_EXPERIMENTAL_PERFORMANCE_EXECUTIVE", "").lower() != "true":
        return
    if not runtime.has_decision(PERFORMANCE_RESPONSE_DECISION_TYPE):
        PERFORMANCE_RESPONSE_IQ_PACK.install(runtime)
    app.include_router(
        build_performance_executive_router(
            ExecutivePerformanceService(
                PerformanceIndustryIQService(
                    performance_service, build_application_service(runtime)
                )
            )
        )
    )

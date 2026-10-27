"""Opt-in experimental read-only executive performance preview endpoint.

Not in /api/v1. Request observations are caller supplied and are never
promoted to verified enterprise evidence or persisted as Decisions.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from .application_contract import ExecutionContext
from .auth import ActorContext, get_actor_context
from .performance_executive import (
    ExecutivePackageRequest,
    ExecutivePerformanceError,
    ExecutivePerformancePackage,
    ExecutivePerformanceService,
)
from .performance_industry_iq import PerformanceReasoningError
from .performance_registry import PerformanceContractRegistryError
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
        # No caller-supplied actor, roles, tenant or authorization claims.
        context = ExecutionContext.from_principal(
            actor,
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
            status = (
                404
                if exc.code in {"REVISION_NOT_FOUND", "ACTIVE_REVISION_NOT_FOUND"}
                else 422
            )
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

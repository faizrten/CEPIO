from __future__ import annotations

import ipaddress
import os

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import api as legacy
from .management_contract import (
    BindingDescriptor,
    CapabilityInventory,
    CEPIOManagementService,
    IndustryIQPackDescriptor,
    ProfileDescriptor,
    RuntimeDescriptor,
    RuntimeHealth,
    SkillDescriptor,
)
from .management_contract import InvestigationOperations
from .management_runtime import build_management_service


MANAGEMENT_API_PREFIX = "/management/v1"


def _is_local_host(host: str | None) -> bool:
    if host is None:
        return False
    if host in {"localhost", "testclient"}:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def create_management_app(service: CEPIOManagementService) -> FastAPI:
    """Create the local-only read-only FastAPI projection of Management Contract v0.1."""

    app = FastAPI(
        title="CEPIO Management API",
        version="0.1.0",
        description=(
            "Local-only read-only CEPIO control-plane projection. This API exposes "
            "durable management descriptors and deliberately excludes runtime mutation."
        ),
    )

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        host = request.client.host if request.client is not None else None
        if not _is_local_host(host):
            return JSONResponse(
                status_code=403,
                content={"detail": "CEPIO Management API v0.1 accepts loopback clients only"},
            )
        return await call_next(request)

    @app.get(f"{MANAGEMENT_API_PREFIX}/health", response_model=RuntimeHealth, tags=["system"])
    def health() -> RuntimeHealth:
        return service.health()

    @app.get(
        f"{MANAGEMENT_API_PREFIX}/status",
        response_model=RuntimeDescriptor,
        tags=["system"],
    )
    def status() -> RuntimeDescriptor:
        return service.runtime_descriptor()

    @app.get(
        f"{MANAGEMENT_API_PREFIX}/capabilities",
        response_model=CapabilityInventory,
        tags=["capabilities"],
    )
    def capabilities() -> CapabilityInventory:
        return service.capabilities()

    @app.get(
        f"{MANAGEMENT_API_PREFIX}/skills",
        response_model=list[SkillDescriptor],
        tags=["capabilities"],
    )
    def skills() -> list[SkillDescriptor]:
        return service.list_skills()

    @app.get(
        f"{MANAGEMENT_API_PREFIX}/industry-iq",
        response_model=list[IndustryIQPackDescriptor],
        tags=["capabilities"],
    )
    def industry_iq() -> list[IndustryIQPackDescriptor]:
        return service.list_industry_iq()

    @app.get(
        f"{MANAGEMENT_API_PREFIX}/bindings",
        response_model=list[BindingDescriptor],
        tags=["configuration"],
    )
    def bindings() -> list[BindingDescriptor]:
        return service.list_bindings()

    @app.get(
        f"{MANAGEMENT_API_PREFIX}/investigations",
        response_model=InvestigationOperations,
        tags=["operations"],
    )
    def investigations() -> InvestigationOperations:
        # Loopback-only management cannot supply an authenticated tenant context.
        return service.investigation_operations()

    @app.get(
        f"{MANAGEMENT_API_PREFIX}/profiles",
        response_model=list[ProfileDescriptor],
        tags=["configuration"],
    )
    def profiles() -> list[ProfileDescriptor]:
        return service.list_profiles()

    return app


service = build_management_service(legacy.runtime)
app = create_management_app(service)


def main() -> None:
    """Run the v0.1 management plane on loopback only."""

    port = int(os.getenv("CEPIO_MANAGEMENT_PORT", "8100"))
    if not 1 <= port <= 65535:
        raise RuntimeError("CEPIO_MANAGEMENT_PORT must be between 1 and 65535")
    uvicorn.run("cepio.management_api:app", host="127.0.0.1", port=port)

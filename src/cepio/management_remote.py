from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .auth import ActorContext, get_actor_context
from .management_contract import (
    BindingDescriptor,
    CapabilityInventory,
    CEPIOManagementService,
    IndustryIQPackDescriptor,
    InvestigationOperations,
    ProfileDescriptor,
    RuntimeDescriptor,
    RuntimeHealth,
    SkillDescriptor,
)


MANAGEMENT_API_PREFIX = "/management/v1"
MANAGEMENT_READ_ROLES = frozenset({"cepio_management_reader", "cepio_admin"})


def require_management_reader(
    actor: ActorContext = Depends(get_actor_context),
) -> ActorContext:
    """Authorize authenticated actors for read-only remote management metadata."""

    if actor.roles.isdisjoint(MANAGEMENT_READ_ROLES):
        raise HTTPException(
            status_code=403,
            detail={
                "code": "management_forbidden",
                "message": "CEPIO management read role is required",
            },
        )
    return actor


def build_remote_management_router(service: CEPIOManagementService) -> APIRouter:
    """Project Management Contract v0.1 as authenticated, GET-only remote routes.

    This router is deliberately additive to the loopback-only management application.
    It exposes the same sanitized descriptors and does not introduce management commands,
    provider credentials, source payloads, or mutation semantics.
    """

    router = APIRouter(
        prefix=MANAGEMENT_API_PREFIX,
        dependencies=[Depends(require_management_reader)],
    )

    @router.get("/health", response_model=RuntimeHealth, tags=["management-system"])
    def health() -> RuntimeHealth:
        return service.health()

    @router.get("/status", response_model=RuntimeDescriptor, tags=["management-system"])
    def status() -> RuntimeDescriptor:
        return service.runtime_descriptor()

    @router.get(
        "/capabilities",
        response_model=CapabilityInventory,
        tags=["management-capabilities"],
    )
    def capabilities() -> CapabilityInventory:
        return service.capabilities()

    @router.get(
        "/skills",
        response_model=list[SkillDescriptor],
        tags=["management-capabilities"],
    )
    def skills() -> list[SkillDescriptor]:
        return service.list_skills()

    @router.get(
        "/industry-iq",
        response_model=list[IndustryIQPackDescriptor],
        tags=["management-capabilities"],
    )
    def industry_iq() -> list[IndustryIQPackDescriptor]:
        return service.list_industry_iq()

    @router.get(
        "/bindings",
        response_model=list[BindingDescriptor],
        tags=["management-configuration"],
    )
    def bindings() -> list[BindingDescriptor]:
        return service.list_bindings()

    @router.get(
        "/profiles",
        response_model=list[ProfileDescriptor],
        tags=["management-configuration"],
    )
    def profiles() -> list[ProfileDescriptor]:
        return service.list_profiles()

    return router

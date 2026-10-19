from __future__ import annotations

from .application_contract import CEPIOApplicationService
from .maintenance_deferral_skill import (
    MAINTENANCE_DEFERRAL_SKILL_ID,
    execute_maintenance_deferral,
    maintenance_deferral_skill_spec,
)
from .runtime import CEPIORuntime
from .skill_preflight import SkillPreflightSpec
from .skill_preflight import SkillRegistry


def shipped_skill_specs() -> tuple[SkillPreflightSpec, ...]:
    """Return the Skill contracts shipped by the current CEPIO application host."""

    return (maintenance_deferral_skill_spec(),)


def shipped_executable_skill_ids() -> frozenset[str]:
    """Return the shipped Skill IDs with an executable host binding."""

    return frozenset({MAINTENANCE_DEFERRAL_SKILL_ID})


def build_application_service(runtime: CEPIORuntime) -> CEPIOApplicationService:
    """Build the shipped CEPIO application layer for one runtime instance.

    Protocol adapters call this builder instead of registering executable Skills
    independently. That keeps REST, MCP, SDK-backed REST calls, and future adapters on
    the same admitted Skill set and execution semantics.
    """

    skills = SkillRegistry(runtime)
    for spec in shipped_skill_specs():
        skills.register(spec)

    service = CEPIOApplicationService(runtime, skill_registry=skills)
    service.register_skill_executor(
        MAINTENANCE_DEFERRAL_SKILL_ID,
        execute_maintenance_deferral,
    )
    return service

from __future__ import annotations

from .application_contract import CEPIOApplicationService
from .maintenance_deferral_skill import (
    MAINTENANCE_DEFERRAL_SKILL_ID,
    execute_maintenance_deferral,
    maintenance_deferral_skill_spec,
)
from .runtime import CEPIORuntime
from .skill_preflight import SkillRegistry


def build_application_service(runtime: CEPIORuntime) -> CEPIOApplicationService:
    """Build the shipped CEPIO application layer for one runtime instance.

    Protocol adapters call this builder instead of registering executable Skills
    independently. That keeps REST, MCP, SDK-backed REST calls, and future adapters on
    the same admitted Skill set and execution semantics.
    """

    skills = SkillRegistry(runtime)
    skills.register(maintenance_deferral_skill_spec())

    service = CEPIOApplicationService(runtime, skill_registry=skills)
    service.register_skill_executor(
        MAINTENANCE_DEFERRAL_SKILL_ID,
        execute_maintenance_deferral,
    )
    return service

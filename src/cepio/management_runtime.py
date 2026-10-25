from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping

from .application_runtime import shipped_executable_skill_ids, shipped_skill_specs
from .auth import AuthSettings
from .config import RuntimeSettings
from .management_contract import (
    BindingDescriptor,
    BindingVerification,
    CEPIOManagementService,
    InvestigationOperations,
)
from .platform_bindings import BindingRegistration
from .runtime import CEPIORuntime


def build_management_service(
    runtime: CEPIORuntime,
    *,
    runtime_settings: RuntimeSettings | None = None,
    auth_settings: AuthSettings | None = None,
    bindings: Iterable[BindingDescriptor] = (),
    binding_inventory_connected: bool = False,
    binding_verifications: Mapping[str, BindingVerification] | None = None,
    remote_access: bool = False,
    investigation_observer: Callable[[str], InvestigationOperations] | None = None,
) -> CEPIOManagementService:
    """Build the read-only CEPIO management contract for one runtime instance."""

    return CEPIOManagementService(
        runtime,
        runtime_settings=runtime_settings or RuntimeSettings.from_env(),
        auth_settings=auth_settings or AuthSettings.from_env(),
        skill_specs=shipped_skill_specs(),
        executable_skill_ids=shipped_executable_skill_ids(),
        bindings=bindings,
        binding_inventory_connected=binding_inventory_connected,
        binding_verifications=binding_verifications,
        remote_access=remote_access,
        investigation_observer=investigation_observer,
    )


def build_management_service_from_registrations(
    runtime: CEPIORuntime,
    *,
    binding_registrations: Iterable[BindingRegistration],
    runtime_settings: RuntimeSettings | None = None,
    auth_settings: AuthSettings | None = None,
) -> CEPIOManagementService:
    """Build Management from canonical Binding Contract registrations."""

    return build_management_service(
        runtime,
        runtime_settings=runtime_settings,
        auth_settings=auth_settings,
        bindings=(
            BindingDescriptor.from_registration(registration)
            for registration in binding_registrations
        ),
        binding_inventory_connected=True,
    )

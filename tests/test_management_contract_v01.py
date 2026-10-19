from __future__ import annotations

from cepio.application_runtime import shipped_executable_skill_ids, shipped_skill_specs
from cepio.auth import AuthSettings
from cepio.bootstrap import build_runtime
from cepio.config import RuntimeSettings
from cepio.management_contract import BindingDescriptor, CEPIOManagementService


def settings(db_url: str = "memory://") -> RuntimeSettings:
    return RuntimeSettings(
        environment="test",
        db_url=db_url,
        resource_root=None,
        ontology_dir=None,
        profiles=(),
        validate_types=True,
        validate_properties=True,
        strict_properties=False,
    )


def auth() -> AuthSettings:
    return AuthSettings(
        mode="dev",
        environment="test",
        tenant_id=None,
        audience=None,
        issuer=None,
        jwks_uri=None,
        group_role_map={},
    )


def service(*, db_url: str = "memory://") -> CEPIOManagementService:
    runtime = build_runtime()
    runtime.industry_iq_packs = {"cepio.iq.example": "1.2.3"}
    runtime.profile_versions = {"profile-a": "0.4.0"}  # type: ignore[attr-defined]
    return CEPIOManagementService(
        runtime,
        runtime_settings=settings(db_url),
        auth_settings=auth(),
        skill_specs=shipped_skill_specs(),
        executable_skill_ids=shipped_executable_skill_ids(),
        bindings=[
            BindingDescriptor(
                binding_id="fabric-dev",
                provider="microsoft-fabric",
                capability="industrial-observation",
                mode="read",
                status="ready",
                authority="observation-only",
            )
        ],
    )


def test_management_contract_exposes_sanitized_runtime_and_health():
    management = service(db_url="sqlite:////tmp/tenant-secret.db")

    health = management.health()
    descriptor = management.runtime_descriptor()

    assert health.status == "healthy"
    assert health.read_only is True
    assert health.local_only is True
    assert health.metadata.contract_version == "0.1.0"
    assert descriptor.environment == "test"
    assert descriptor.persistence_mode == "sqlite"
    assert descriptor.auth_mode == "dev"
    assert "tenant-secret" not in descriptor.model_dump_json()


def test_management_contract_classifies_memory_and_external_persistence():
    assert service().runtime_descriptor().persistence_mode == "memory"
    assert service(db_url="postgresql://opaque").runtime_descriptor().persistence_mode == "external"


def test_management_contract_lists_durable_capability_descriptors():
    management = service()

    skills = management.list_skills()
    packs = management.list_industry_iq()
    bindings = management.list_bindings()
    profiles = management.list_profiles()
    capabilities = management.capabilities()

    assert len(skills) == 1
    assert skills[0].skill_id == "cepio.skill.maintenance.assess-maintenance-deferral"
    assert skills[0].executable is True
    assert skills[0].authority.propose_decision is True
    assert skills[0].authority.execute_actions == []
    assert skills[0].authority.approval_required_for == ["defer-work-order"]
    assert skills[0].decision_capabilities == ["maintenance-deferral-decision"]
    assert skills[0].action_capabilities == ["defer-work-order"]

    assert [(pack.pack_id, pack.version) for pack in packs] == [("cepio.iq.example", "1.2.3")]
    assert bindings[0].binding_id == "fabric-dev"
    assert bindings[0].authority == "observation-only"
    assert [(profile.profile_id, profile.version) for profile in profiles] == [
        ("profile-a", "0.4.0")
    ]
    assert capabilities.skill_count == 1
    assert capabilities.executable_skill_count == 1
    assert capabilities.industry_iq_pack_count == 1
    assert capabilities.binding_count == 1
    assert capabilities.profile_count == 1
    assert capabilities.management_contract == "0.1.0"


def test_management_contract_does_not_infer_bindings_or_invalid_profile_state():
    runtime = build_runtime()
    management = CEPIOManagementService(
        runtime,
        runtime_settings=settings(),
        auth_settings=auth(),
        skill_specs=(),
        executable_skill_ids=(),
    )

    assert management.list_bindings() == []
    runtime.profile_versions = "not-a-map"  # type: ignore[attr-defined]
    assert management.list_profiles() == []
    capabilities = management.capabilities()
    assert capabilities.skill_count == 0
    assert capabilities.executable_skill_count == 0

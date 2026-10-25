from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ._version import __version__
from .auth import AuthSettings
from .config import RuntimeSettings
from .platform_bindings import (
    BINDING_CONTRACT_VERSION,
    BindingMode,
    BindingRegistration,
)
from .runtime import CEPIORuntime
from .skill_preflight import SkillPreflightSpec


MANAGEMENT_CONTRACT_VERSION: Literal["0.1.0"] = "0.1.0"


class ManagementMetadata(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract_version: Literal["0.1.0"] = MANAGEMENT_CONTRACT_VERSION


class RuntimeHealth(BaseModel):
    status: Literal["healthy"] = "healthy"
    read_only: bool = True
    local_only: bool = True
    scope: Literal["process-only"] = "process-only"
    metadata: ManagementMetadata = Field(default_factory=ManagementMetadata)


class RuntimeDescriptor(BaseModel):
    cepio_version: str
    environment: str
    persistence_mode: Literal["memory", "sqlite", "external"]
    application_auth_mode: str
    management_access: Literal["loopback-only", "authenticated-remote"] = "loopback-only"
    validate_types: bool
    validate_properties: bool
    strict_properties: bool
    metadata: ManagementMetadata = Field(default_factory=ManagementMetadata)


class SkillAuthorityDescriptor(BaseModel):
    recommend: bool
    propose_decision: bool
    execute_actions: list[str] = Field(default_factory=list)
    approval_required_for: list[str] = Field(default_factory=list)


class SkillDescriptor(BaseModel):
    skill_id: str
    binding_id: str | None = None
    executable: bool
    readiness: Literal["actor-preflight-required"] = "actor-preflight-required"
    required_industry_iq: dict[str, str] = Field(default_factory=dict)
    decision_capabilities: list[str] = Field(default_factory=list)
    action_capabilities: list[str] = Field(default_factory=list)
    authority: SkillAuthorityDescriptor


class IndustryIQPackDescriptor(BaseModel):
    pack_id: str
    version: str
    deployment_recorded: bool = False
    requires_core: str | None = None
    requires_packs: dict[str, str] = Field(default_factory=dict)
    functions: list[str] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)


class BindingVerification(BaseModel):
    """Server-supplied evidence from a completed, scoped and non-destructive probe."""

    binding_id: str
    result: Literal["passed", "failed"]
    checked_at: datetime
    expires_at: datetime
    evidence_ref: str


class BindingDescriptor(BaseModel):
    """Management projection of an explicitly registered Binding Contract."""

    binding_id: str
    provider: str
    capability: str
    mode: Literal["read", "write", "read-write"]
    status: Literal["ready", "degraded", "not-configured"]
    authority: str
    source_system: str | None = None
    declared_capabilities: list[str] = Field(default_factory=list)
    binding_contract_version: str = BINDING_CONTRACT_VERSION
    # Registration status is not proof of live source connectivity.
    verified_readiness: Literal["not-verified", "verified", "failed", "stale"] = "not-verified"
    last_checked_at: datetime | None = None
    verification_ref: str | None = None

    @classmethod
    def from_registration(cls, registration: BindingRegistration) -> "BindingDescriptor":
        manifest = registration.manifest
        mode: Literal["read", "write", "read-write"]
        if manifest.mode == BindingMode.evidence:
            mode = "read"
        else:
            mode = "write"
        return cls(
            binding_id=manifest.binding_id,
            provider=manifest.provider_id,
            capability=registration.capability_id,
            mode=mode,
            status=registration.status.value,
            authority=registration.authority,
            source_system=manifest.source_system,
            declared_capabilities=list(registration.declared_capabilities),
            binding_contract_version=registration.contract_version,
        )


class ProfileDescriptor(BaseModel):
    profile_id: str
    version: str


class CapabilityInventory(BaseModel):
    skill_count: int
    executable_skill_count: int
    industry_iq_pack_count: int
    binding_count: int
    profile_count: int
    registered_function_count: int = 0
    registered_decision_count: int = 0
    registered_action_count: int = 0
    binding_inventory_state: Literal["connected", "not-wired"] = "not-wired"
    skill_inventory_source: Literal["shipped-specifications"] = "shipped-specifications"
    readiness_qualified: bool = False
    application_contract_available: bool = True
    management_contract_version: str = MANAGEMENT_CONTRACT_VERSION
    binding_contract_version: str = BINDING_CONTRACT_VERSION


class InvestigationOperations(BaseModel):
    """No customer records; only a trusted, tenant-scoped aggregate may populate counts."""

    state: Literal["not-connected", "available", "degraded"] = "not-connected"
    counts: dict[str, int] | None = None
    tenant_id: str | None = None
    observed_at: datetime | None = None
    reason: str = "No tenant-scoped investigation operations observer configured"


class CEPIOManagementService:
    """Read-only protocol-neutral management view over one CEPIO runtime.

    The service exposes durable descriptors rather than private runtime dictionaries.
    Bindings are explicit host-supplied descriptors so repository support for a provider
    is never confused with a configured/live customer binding.
    """

    def __init__(
        self,
        runtime: CEPIORuntime,
        *,
        runtime_settings: RuntimeSettings,
        auth_settings: AuthSettings,
        skill_specs: Iterable[SkillPreflightSpec] = (),
        executable_skill_ids: Iterable[str] = (),
        bindings: Iterable[BindingDescriptor] = (),
        binding_inventory_connected: bool = False,
        binding_verifications: Mapping[str, BindingVerification] | None = None,
        remote_access: bool = False,
        investigation_observer: Callable[[str], InvestigationOperations] | None = None,
    ) -> None:
        self.runtime = runtime
        self.runtime_settings = runtime_settings
        self.auth_settings = auth_settings
        self._skill_specs = tuple(skill_specs)
        self._executable_skill_ids = frozenset(executable_skill_ids)
        self._bindings = tuple(bindings)
        self._binding_inventory_connected = binding_inventory_connected
        self._binding_verifications = dict(binding_verifications or {})
        self._remote_access = remote_access
        self._investigation_observer = investigation_observer

    def health(self) -> RuntimeHealth:
        return RuntimeHealth(local_only=not self._remote_access)

    def runtime_descriptor(self) -> RuntimeDescriptor:
        db_url = self.runtime_settings.db_url
        if db_url == "memory://":
            persistence_mode: Literal["memory", "sqlite", "external"] = "memory"
        elif db_url.startswith("sqlite:///"):
            persistence_mode = "sqlite"
        else:
            persistence_mode = "external"
        return RuntimeDescriptor(
            cepio_version=__version__,
            environment=self.runtime_settings.environment,
            persistence_mode=persistence_mode,
            application_auth_mode=self.auth_settings.mode,
            validate_types=self.runtime_settings.validate_types,
            validate_properties=self.runtime_settings.validate_properties,
            strict_properties=self.runtime_settings.strict_properties,
            management_access="authenticated-remote" if self._remote_access else "loopback-only",
        )

    def list_skills(self) -> list[SkillDescriptor]:
        result: list[SkillDescriptor] = []
        for spec in sorted(self._skill_specs, key=lambda item: item.skill_id):
            required_iq = {
                pack_id: spec.industry_iq_pack_constraints.get(pack_id, "*")
                for pack_id in sorted(
                    set(spec.industry_iq_packs) | set(spec.industry_iq_pack_constraints)
                )
            }
            result.append(
                SkillDescriptor(
                    skill_id=spec.skill_id,
                    binding_id=spec.binding_id,
                    executable=spec.skill_id in self._executable_skill_ids,
                    required_industry_iq=required_iq,
                    decision_capabilities=sorted(spec.decisions),
                    action_capabilities=sorted(spec.actions),
                    authority=SkillAuthorityDescriptor(
                        recommend=spec.authority.recommend,
                        propose_decision=spec.authority.propose_decision,
                        execute_actions=sorted(spec.authority.execute_actions),
                        approval_required_for=sorted(spec.authority.approval_required_for),
                    ),
                )
            )
        return result

    def list_industry_iq(self) -> list[IndustryIQPackDescriptor]:
        deployment = getattr(self.runtime, "industry_iq_deployment_manifest", None)
        manifests = getattr(deployment, "packs", {}) if deployment is not None else {}
        result: list[IndustryIQPackDescriptor] = []
        for pack_id, version in sorted(self.runtime.industry_iq_packs.items()):
            manifest = manifests.get(pack_id) if isinstance(manifests, dict) else None
            # Never attach a deployment manifest for a different version.
            valid = manifest is not None and manifest.version == version
            if valid and manifest is not None:
                result.append(
                    IndustryIQPackDescriptor(
                        pack_id=pack_id,
                        version=version,
                        deployment_recorded=True,
                        requires_core=manifest.requires_core,
                        requires_packs=dict(manifest.requires_packs),
                        functions=sorted(manifest.functions),
                        decisions=sorted(manifest.decisions),
                        actions=sorted(manifest.actions),
                    )
                )
            else:
                result.append(IndustryIQPackDescriptor(pack_id=pack_id, version=version))
        return result

    def list_bindings(self) -> list[BindingDescriptor]:
        now = datetime.now(timezone.utc)
        result: list[BindingDescriptor] = []
        for binding in sorted(self._bindings, key=lambda item: item.binding_id):
            probe = self._binding_verifications.get(binding.binding_id)
            if probe is None or probe.binding_id != binding.binding_id:
                result.append(binding.model_copy(update={"verified_readiness": "not-verified"}))
                continue
            checked = probe.checked_at
            expires = probe.expires_at
            if (
                checked.tzinfo is None
                or expires.tzinfo is None
                or checked > now
                or expires <= checked
                or not probe.evidence_ref.strip()
            ):
                readiness = "not-verified"
            elif expires <= now:
                readiness = "stale"
            elif probe.result == "passed" and binding.status == "ready":
                readiness = "verified"
            else:
                readiness = "failed"
            result.append(
                binding.model_copy(
                    update={
                        "verified_readiness": readiness,
                        "last_checked_at": checked if readiness != "not-verified" else None,
                        "verification_ref": probe.evidence_ref
                        if readiness != "not-verified"
                        else None,
                    }
                )
            )
        return result

    def investigation_operations(self, tenant_id: str | None = None) -> InvestigationOperations:
        if self._investigation_observer is None or not tenant_id:
            return InvestigationOperations()
        try:
            snapshot = InvestigationOperations.model_validate(
                self._investigation_observer(tenant_id)
            )
            if snapshot.tenant_id != tenant_id:
                return InvestigationOperations(
                    state="degraded", reason="Investigation scope mismatch"
                )
            if (
                snapshot.state != "available"
                or snapshot.observed_at is None
                or snapshot.counts is None
            ):
                return InvestigationOperations(
                    state="degraded", reason="Observer returned incomplete operational evidence"
                )
            if snapshot.observed_at.tzinfo is None or snapshot.observed_at > datetime.now(
                timezone.utc
            ):
                return InvestigationOperations(
                    state="degraded", reason="Observer timestamp is invalid"
                )
            if any(
                not key or type(value) is not int or value < 0
                for key, value in snapshot.counts.items()
            ):
                return InvestigationOperations(
                    state="degraded", reason="Observer counts are invalid"
                )
            return snapshot
        except Exception:
            return InvestigationOperations(state="degraded", reason="Trusted observer unavailable")

    def list_profiles(self) -> list[ProfileDescriptor]:
        profile_versions = getattr(self.runtime, "profile_versions", {})
        if not isinstance(profile_versions, dict):
            return []
        return [
            ProfileDescriptor(profile_id=str(profile_id), version=str(version))
            for profile_id, version in sorted(profile_versions.items())
        ]

    def capabilities(self) -> CapabilityInventory:
        skills = self.list_skills()
        return CapabilityInventory(
            skill_count=len(skills),
            executable_skill_count=sum(1 for skill in skills if skill.executable),
            industry_iq_pack_count=len(self.runtime.industry_iq_packs),
            binding_count=len(self._bindings),
            profile_count=len(self.list_profiles()),
            registered_function_count=len(getattr(self.runtime, "_functions", {})),
            registered_decision_count=len(getattr(self.runtime, "_decisions", {})),
            registered_action_count=len(getattr(self.runtime, "_actions", {})),
            binding_inventory_state="connected"
            if self._binding_inventory_connected
            else "not-wired",
        )

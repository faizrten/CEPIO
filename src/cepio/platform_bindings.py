"""Thin, provider-neutral contracts for CEPIO platform bindings.

Platform bindings connect authoritative external systems to the CEPIO operating
contract. They deliberately do not own Industry IQ reasoning or provider business
semantics. Evidence bindings preserve external identity/provenance; side-effecting
bindings use the existing governed Action Runtime adapter contract.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .adapters import GovernedWriteAdapter
from .domain_bindings import ExternalRecordReference
from .external_actions import ExternalActionRuntime, ExternalActionStatus


BINDING_CONTRACT_VERSION: Literal["0.1"] = "0.1"


class BindingMode(str, Enum):
    evidence = "evidence"
    governed_action = "governed-action"


class BindingCapability(str, Enum):
    resolve_evidence = "resolve-evidence"
    versioned_identity = "versioned-identity"
    governed_write = "governed-write"
    verify = "verify"
    reconcile = "reconcile"


class BindingRuntimeStatus(str, Enum):
    ready = "ready"
    degraded = "degraded"
    not_configured = "not-configured"


class UnsupportedBindingCapability(RuntimeError):
    """Raised when a binding is asked to perform an undeclared capability."""


class BindingConformanceError(RuntimeError):
    """Raised when a platform binding violates the CEPIO binding contract."""


class PlatformBindingManifest(BaseModel):
    """Invariant declaration for one CEPIO platform binding implementation."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["0.1"] = BINDING_CONTRACT_VERSION
    binding_id: str
    provider_id: str
    source_system: str
    mode: BindingMode
    capabilities: frozenset[BindingCapability]

    @model_validator(mode="after")
    def validate_mode_capabilities(self) -> "PlatformBindingManifest":
        if (
            not self.binding_id.strip()
            or not self.provider_id.strip()
            or not self.source_system.strip()
        ):
            raise ValueError("binding_id, provider_id and source_system must be non-empty")

        if self.mode == BindingMode.evidence:
            required = {BindingCapability.resolve_evidence}
            forbidden = {
                BindingCapability.governed_write,
                BindingCapability.verify,
                BindingCapability.reconcile,
            }
        else:
            required = {
                BindingCapability.governed_write,
                BindingCapability.verify,
                BindingCapability.reconcile,
            }
            forbidden = {BindingCapability.resolve_evidence}

        missing = required.difference(self.capabilities)
        if missing:
            names = ", ".join(sorted(item.value for item in missing))
            raise ValueError(f"{self.mode.value} binding is missing required capabilities: {names}")

        invalid = forbidden.intersection(self.capabilities)
        if invalid:
            names = ", ".join(sorted(item.value for item in invalid))
            raise ValueError(f"{self.mode.value} binding declares forbidden capabilities: {names}")
        return self

    def require(self, capability: BindingCapability) -> None:
        if capability not in self.capabilities:
            raise UnsupportedBindingCapability(
                f"Binding {self.binding_id!r} does not declare {capability.value!r}"
            )


class BindingRegistration(BaseModel):
    """Explicit runtime registration of a binding capability.

    The manifest describes what an implementation guarantees. Registration records
    which industrial capability the host intentionally exposes and its current runtime
    status. Provider support in the repository is never sufficient to create a
    registration by itself.
    """

    model_config = ConfigDict(frozen=True)

    contract_version: Literal["0.1"] = BINDING_CONTRACT_VERSION
    manifest: PlatformBindingManifest
    capability_id: str
    status: BindingRuntimeStatus = BindingRuntimeStatus.ready

    @model_validator(mode="after")
    def validate_registration(self) -> "BindingRegistration":
        if not self.capability_id.strip():
            raise ValueError("capability_id must be non-empty")
        return self

    @property
    def access_mode(self) -> Literal["read", "write"]:
        if self.manifest.mode == BindingMode.evidence:
            return "read"
        return "write"

    @property
    def authority(self) -> Literal["observation-only", "governed-action"]:
        if self.manifest.mode == BindingMode.evidence:
            return "observation-only"
        return "governed-action"

    @property
    def declared_capabilities(self) -> tuple[str, ...]:
        return tuple(sorted(capability.value for capability in self.manifest.capabilities))


class EvidenceEnvelope(BaseModel):
    """Normalized evidence plus the immutable source record that proves its origin.

    The payload is intentionally opaque to Core. Domain interpretation belongs in
    Industry IQ; bulk source payloads should remain in the authoritative platform.
    """

    reference: ExternalRecordReference
    evidence: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class EvidenceBinding(Protocol):
    manifest: PlatformBindingManifest

    def resolve_evidence(self, external_id: str) -> EvidenceEnvelope: ...


class EvidenceConformanceResult(BaseModel):
    binding_id: str
    reference_key: str
    versioned: bool


class GovernedActionConformanceResult(BaseModel):
    binding_id: str
    execution_id: str
    verification_path: Literal["verify", "reconcile"]
    status: ExternalActionStatus
    dispatch_attempts: int
    verification_attempts: int


def register_evidence_binding(
    binding: EvidenceBinding,
    *,
    capability_id: str,
    status: BindingRuntimeStatus = BindingRuntimeStatus.ready,
) -> BindingRegistration:
    """Create an explicit registration for an evidence binding without reading data."""

    manifest = binding.manifest
    if manifest.mode != BindingMode.evidence:
        raise BindingConformanceError("Evidence registration requires an evidence binding manifest")
    manifest.require(BindingCapability.resolve_evidence)
    if not callable(getattr(binding, "resolve_evidence", None)):
        raise BindingConformanceError("Evidence binding does not implement resolve_evidence()")
    if hasattr(binding, "write_governed"):
        raise BindingConformanceError(
            "Evidence-only bindings must not expose the governed write interface"
        )
    return BindingRegistration(
        manifest=manifest,
        capability_id=capability_id,
        status=status,
    )


def register_governed_action_binding(
    adapter: GovernedWriteAdapter,
    manifest: PlatformBindingManifest,
    *,
    capability_id: str,
    status: BindingRuntimeStatus = BindingRuntimeStatus.ready,
) -> BindingRegistration:
    """Create an explicit registration after validating the governed adapter shape."""

    qualify_governed_action_adapter(adapter, manifest)
    return BindingRegistration(
        manifest=manifest,
        capability_id=capability_id,
        status=status,
    )


def qualify_evidence_binding(
    binding: EvidenceBinding,
    *,
    external_id: str,
) -> EvidenceConformanceResult:
    """Exercise source-neutral identity/provenance invariants for one evidence record."""

    manifest = binding.manifest
    if manifest.mode != BindingMode.evidence:
        raise BindingConformanceError("Evidence conformance requires an evidence binding manifest")
    manifest.require(BindingCapability.resolve_evidence)

    if hasattr(binding, "write_governed"):
        raise BindingConformanceError(
            "Evidence-only bindings must not expose the governed write interface"
        )

    envelope = binding.resolve_evidence(external_id)
    reference = envelope.reference
    if reference.source_system != manifest.source_system:
        raise BindingConformanceError(
            "Evidence source_system does not match the binding manifest: "
            f"{reference.source_system!r} != {manifest.source_system!r}"
        )
    if reference.record_id != external_id:
        raise BindingConformanceError(
            f"Evidence record identity changed: {reference.record_id!r} != {external_id!r}"
        )

    versioned = reference.record_version is not None
    if BindingCapability.versioned_identity in manifest.capabilities and not versioned:
        raise BindingConformanceError(
            "Binding declares versioned-identity but returned no record_version"
        )

    return EvidenceConformanceResult(
        binding_id=manifest.binding_id,
        reference_key=reference.stable_key,
        versioned=versioned,
    )


def qualify_governed_action_adapter(
    adapter: GovernedWriteAdapter,
    manifest: PlatformBindingManifest,
) -> None:
    """Validate adapter shape without dispatching an external write."""

    if manifest.mode != BindingMode.governed_action:
        raise BindingConformanceError(
            "Governed-action conformance requires a governed-action binding manifest"
        )
    for capability in (
        BindingCapability.governed_write,
        BindingCapability.verify,
        BindingCapability.reconcile,
    ):
        manifest.require(capability)

    if adapter.system_name != manifest.source_system:
        raise BindingConformanceError(
            "Adapter system_name does not match the binding manifest: "
            f"{adapter.system_name!r} != {manifest.source_system!r}"
        )
    for method_name in ("write_governed", "verify_write", "reconcile_write"):
        if not callable(getattr(adapter, method_name, None)):
            raise BindingConformanceError(
                f"Governed-action adapter does not implement {method_name}()"
            )


def qualify_governed_action_execution(
    external_runtime: ExternalActionRuntime,
    manifest: PlatformBindingManifest,
    *,
    execution_id: str,
    verification_path: Literal["verify", "reconcile"] = "verify",
) -> GovernedActionConformanceResult:
    """Qualify one external execution strictly through the governed Action Runtime."""

    if manifest.mode != BindingMode.governed_action:
        raise BindingConformanceError(
            "Governed-action execution requires a governed-action binding manifest"
        )
    for capability in (
        BindingCapability.governed_write,
        BindingCapability.verify,
        BindingCapability.reconcile,
    ):
        manifest.require(capability)

    queued = external_runtime.get_execution(execution_id)
    if queued.system != manifest.source_system:
        raise BindingConformanceError(
            "External execution system does not match the binding manifest"
        )
    if queued.status != ExternalActionStatus.pending_execution:
        raise BindingConformanceError("Conformance execution must start in pending_execution state")

    dispatched = external_runtime.dispatch(execution_id)
    replay = external_runtime.dispatch(execution_id)
    if replay.dispatch_attempts != dispatched.dispatch_attempts:
        raise BindingConformanceError(
            "Repeated dispatch advanced the external execution attempt count"
        )
    if dispatched.dispatch_attempts != 1:
        raise BindingConformanceError("Conformance execution must dispatch exactly once")

    if verification_path == "verify":
        terminal = external_runtime.verify(execution_id)
    else:
        terminal = external_runtime.reconcile(execution_id)
    if terminal.status != ExternalActionStatus.verified:
        raise BindingConformanceError(
            f"{verification_path} did not produce a verified external outcome"
        )

    return GovernedActionConformanceResult(
        binding_id=manifest.binding_id,
        execution_id=terminal.id,
        verification_path=verification_path,
        status=terminal.status,
        dispatch_attempts=terminal.dispatch_attempts,
        verification_attempts=terminal.verification_attempts,
    )

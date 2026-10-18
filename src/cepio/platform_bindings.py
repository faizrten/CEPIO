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

from .adapters import (
    GovernedVerificationRequest,
    GovernedVerificationResult,
    GovernedWriteAdapter,
    GovernedWriteReceipt,
    GovernedWriteRequest,
)
from .domain_bindings import ExternalRecordReference


class BindingMode(str, Enum):
    evidence = "evidence"
    governed_action = "governed-action"


class BindingCapability(str, Enum):
    resolve_evidence = "resolve-evidence"
    versioned_identity = "versioned-identity"
    governed_write = "governed-write"
    verify = "verify"
    reconcile = "reconcile"


class UnsupportedBindingCapability(RuntimeError):
    """Raised when a binding is asked to perform an undeclared capability."""


class BindingConformanceError(RuntimeError):
    """Raised when a platform binding violates the CEPIO binding contract."""


class PlatformBindingManifest(BaseModel):
    """Minimal declaration for an internal CEPIO platform binding."""

    model_config = ConfigDict(frozen=True)

    schema_version: Literal["0.1"] = "0.1"
    binding_id: str
    provider_id: str
    source_system: str
    mode: BindingMode
    capabilities: frozenset[BindingCapability]

    @model_validator(mode="after")
    def validate_mode_capabilities(self) -> "PlatformBindingManifest":
        if not self.binding_id.strip() or not self.provider_id.strip() or not self.source_system.strip():
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
    receipt: GovernedWriteReceipt
    verification: GovernedVerificationResult
    reconciliation: GovernedVerificationResult


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


def qualify_governed_action_binding(
    adapter: GovernedWriteAdapter,
    manifest: PlatformBindingManifest,
    *,
    write_request: GovernedWriteRequest,
    verification_request: GovernedVerificationRequest,
) -> GovernedActionConformanceResult:
    """Exercise the existing write/verify/reconcile contract without creating a new runtime."""

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
    if write_request.system != adapter.system_name:
        raise BindingConformanceError("Write request system does not match the adapter")
    if verification_request.idempotency_key != write_request.idempotency_key:
        raise BindingConformanceError("Verification must preserve the write idempotency key")

    first = adapter.write_governed(write_request)
    second = adapter.write_governed(write_request)
    if first != second:
        raise BindingConformanceError(
            "Repeated governed write with the same idempotency key changed its receipt"
        )

    effective_verification = verification_request.model_copy(
        update={"source_request_id": first.source_request_id}
    )
    verification = adapter.verify_write(effective_verification)
    reconciliation = adapter.reconcile_write(effective_verification)

    return GovernedActionConformanceResult(
        binding_id=manifest.binding_id,
        receipt=first,
        verification=verification,
        reconciliation=reconciliation,
    )

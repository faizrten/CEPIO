from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field


@dataclass
class AdapterResult:
    system: str
    operation: str
    dry_run: bool = True
    accepted: bool = True
    payload: dict[str, Any] = field(default_factory=dict)


class AdapterVerificationStatus(str, Enum):
    verified = "verified"
    not_applied = "not_applied"
    unknown = "unknown"
    conflict = "conflict"


class GovernedWriteRequest(BaseModel):
    execution_id: str
    system: str
    operation: str
    external_id: str
    canonical_object_id: str
    action_id: str
    actor_id: str
    decision_id: str | None = None
    idempotency_key: str
    payload: dict[str, Any] = Field(default_factory=dict)


class GovernedWriteReceipt(BaseModel):
    accepted: bool = True
    source_request_id: str | None = None
    message: str | None = None
    source_payload: dict[str, Any] = Field(default_factory=dict)


class GovernedVerificationRequest(BaseModel):
    execution_id: str
    system: str
    operation: str
    external_id: str
    canonical_object_id: str
    action_id: str
    idempotency_key: str
    source_request_id: str | None = None
    expected_payload: dict[str, Any] = Field(default_factory=dict)


class GovernedVerificationResult(BaseModel):
    status: AdapterVerificationStatus
    message: str | None = None
    source_payload: dict[str, Any] = Field(default_factory=dict)


class GovernedWriteAdapter(Protocol):
    system_name: str

    def write_governed(self, request: GovernedWriteRequest) -> GovernedWriteReceipt: ...
    def verify_write(self, request: GovernedVerificationRequest) -> GovernedVerificationResult: ...
    def reconcile_write(self, request: GovernedVerificationRequest) -> GovernedVerificationResult: ...


class EnterpriseAdapter(Protocol):
    system_name: str

    def read(self, external_id: str) -> dict[str, Any]: ...
    def write(self, operation: str, payload: dict[str, Any]) -> AdapterResult: ...


class DryRunAdapter:
    system_name = "generic"

    def __init__(self) -> None:
        self._governed_receipts: dict[str, GovernedWriteReceipt] = {}

    def read(self, external_id: str) -> dict[str, Any]:
        return {"external_id": external_id, "system": self.system_name, "status": "stub"}

    def write(self, operation: str, payload: dict[str, Any]) -> AdapterResult:
        return AdapterResult(system=self.system_name, operation=operation, dry_run=True, payload=payload)

    def write_governed(self, request: GovernedWriteRequest) -> GovernedWriteReceipt:
        prior = self._governed_receipts.get(request.idempotency_key)
        if prior is not None:
            return prior.model_copy(deep=True)
        receipt = GovernedWriteReceipt(
            accepted=True,
            source_request_id=f"DRY-{uuid4().hex[:12].upper()}",
            message="Dry-run adapter accepted governed write",
            source_payload={"dry_run": True, "external_id": request.external_id},
        )
        self._governed_receipts[request.idempotency_key] = receipt.model_copy(deep=True)
        return receipt

    def verify_write(self, request: GovernedVerificationRequest) -> GovernedVerificationResult:
        receipt = self._governed_receipts.get(request.idempotency_key)
        if receipt is None:
            return GovernedVerificationResult(
                status=AdapterVerificationStatus.not_applied,
                message="No dry-run receipt exists for the idempotency key",
            )
        return GovernedVerificationResult(
            status=AdapterVerificationStatus.verified,
            message="Dry-run write verified",
            source_payload={"dry_run": True, "source_request_id": receipt.source_request_id},
        )

    def reconcile_write(self, request: GovernedVerificationRequest) -> GovernedVerificationResult:
        return self.verify_write(request)


class FakeGovernedWriteAdapter(DryRunAdapter):
    """Deterministic contract-test adapter for governed write/verify/reconcile flows."""

    def __init__(self, system_name: str = "fake_eam") -> None:
        super().__init__()
        self.system_name = system_name
        self.write_calls: list[GovernedWriteRequest] = []
        self.verify_calls: list[GovernedVerificationRequest] = []
        self.reconcile_calls: list[GovernedVerificationRequest] = []
        self.raise_on_write: Exception | None = None
        self.raise_on_verify: Exception | None = None
        self.raise_on_reconcile: Exception | None = None
        self.reject_writes = False
        self.verification_status = AdapterVerificationStatus.verified
        self.reconciliation_status: AdapterVerificationStatus | None = None

    def write_governed(self, request: GovernedWriteRequest) -> GovernedWriteReceipt:
        prior = self._governed_receipts.get(request.idempotency_key)
        if prior is not None:
            return prior.model_copy(deep=True)
        self.write_calls.append(request.model_copy(deep=True))
        if self.raise_on_write is not None:
            raise self.raise_on_write
        receipt = GovernedWriteReceipt(
            accepted=not self.reject_writes,
            source_request_id=f"FAKE-{len(self.write_calls):06d}",
            message="accepted" if not self.reject_writes else "rejected",
            source_payload={
                "external_id": request.external_id,
                "operation": request.operation,
                "idempotency_key": request.idempotency_key,
            },
        )
        if receipt.accepted:
            self._governed_receipts[request.idempotency_key] = receipt.model_copy(deep=True)
        return receipt

    def verify_write(self, request: GovernedVerificationRequest) -> GovernedVerificationResult:
        self.verify_calls.append(request.model_copy(deep=True))
        if self.raise_on_verify is not None:
            raise self.raise_on_verify
        return GovernedVerificationResult(
            status=self.verification_status,
            message=f"verification={self.verification_status.value}",
            source_payload={"source_request_id": request.source_request_id},
        )

    def reconcile_write(self, request: GovernedVerificationRequest) -> GovernedVerificationResult:
        self.reconcile_calls.append(request.model_copy(deep=True))
        if self.raise_on_reconcile is not None:
            raise self.raise_on_reconcile
        status = self.reconciliation_status or self.verification_status
        return GovernedVerificationResult(
            status=status,
            message=f"reconciliation={status.value}",
            source_payload={"source_request_id": request.source_request_id},
        )


class SAPS4HANAAdapter(DryRunAdapter):
    system_name = "sap_s4hana_eam"


class AVEVAPIAdapter(DryRunAdapter):
    system_name = "aveva_pi"


class OSDUAdapter(DryRunAdapter):
    system_name = "osdu"


class PrimaveraP6Adapter(DryRunAdapter):
    system_name = "primavera_p6"


class FabricOneLakeAdapter(DryRunAdapter):
    system_name = "fabric_onelake"

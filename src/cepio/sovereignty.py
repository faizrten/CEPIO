"""Versioned source-use authorization primitive (ADR-006/007/0044).

This is a source-neutral *enforcement input*, not an identity provider, consent
collection service or proof that a caller supplied authentic rights. Production
hosts must provide a verified, immutable source-rights snapshot.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator


class SourceClass(str, Enum):
    PUBLIC = "PUBLIC"
    CEPIO = "CEPIO"
    CUSTOMER = "CUSTOMER"
    CUSTOMER_DERIVED = "CUSTOMER_DERIVED"


class PermittedUse(str, Enum):
    TENANT_INFERENCE = "TENANT_INFERENCE"
    TENANT_ADAPTATION = "TENANT_ADAPTATION"
    SHARED_RETRIEVAL = "SHARED_RETRIEVAL"
    GLOBAL_LEARNING = "GLOBAL_LEARNING"
    EVALUATION = "EVALUATION"
    EXPORT = "EXPORT"


class SovereigntyDenied(PermissionError):
    """Source use is not authorized. Do not expose source metadata in errors."""


class IntelligenceSovereigntyContract(BaseModel):
    """Rights for one source or derivative. These are inputs, not proof of consent."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = "0.1"
    source_id: str = Field(min_length=1)
    owner_id: str = Field(min_length=1)
    source_class: SourceClass
    tenant_id: str | None = None
    rights_basis_ref: str = Field(min_length=1)
    permitted_uses: frozenset[PermittedUse] = Field(default_factory=frozenset)
    parent_source_ids: frozenset[str] = Field(default_factory=frozenset)
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    reviewer_ref: str | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "IntelligenceSovereigntyContract":
        if self.version != "0.1":
            raise ValueError("unsupported sovereignty contract version")
        customer = self.source_class in {SourceClass.CUSTOMER, SourceClass.CUSTOMER_DERIVED}
        if customer != bool(self.tenant_id):
            raise ValueError("customer class requires tenant_id; public/CEPIO cannot declare one")
        if self.source_class == SourceClass.CUSTOMER_DERIVED and not self.parent_source_ids:
            raise ValueError("customer derivative requires parent lineage")
        if self.source_id in self.parent_source_ids:
            raise ValueError("source cannot derive from itself")
        if any(
            value.tzinfo is None or value.utcoffset() is None
            for value in (self.expires_at, self.revoked_at)
            if value is not None
        ):
            raise ValueError("sovereignty times must be timezone-aware")
        return self


def authorize_source_use(
    source_id: str,
    *,
    records: Mapping[str, IntelligenceSovereigntyContract],
    use: PermittedUse,
    tenant_id: str | None,
    at: datetime,
    _ancestors: frozenset[str] = frozenset(),
) -> None:
    """Deny by default; every parent must independently permit the requested use.

    The registry passed here must come from a trusted rights authority, not a
    model output, user request, mutable search index or promotion candidate.
    """
    if at.tzinfo is None or at.utcoffset() is None:
        raise SovereigntyDenied("invalid authorization time")
    if not source_id or source_id in _ancestors:
        raise SovereigntyDenied("missing or cyclic source lineage")
    record = records.get(source_id)
    if not isinstance(record, IntelligenceSovereigntyContract):
        raise SovereigntyDenied("unverified or missing source permission")
    try:
        # Reject forged model_copy(update=...) contracts, which bypass Pydantic
        # validation even for frozen models.
        record = IntelligenceSovereigntyContract.model_validate(dict(vars(record)))
    except (ValidationError, ValueError, TypeError) as exc:
        raise SovereigntyDenied("invalid source rights record") from exc
    if record.source_id != source_id:
        raise SovereigntyDenied("mismatched source permission")
    if len(_ancestors) > 127:
        raise SovereigntyDenied("source lineage depth exceeded")
    if (record.expires_at is not None and at >= record.expires_at) or (
        record.revoked_at is not None and at >= record.revoked_at
    ):
        raise SovereigntyDenied("source permission expired or revoked")
    if not isinstance(use, PermittedUse) or use not in record.permitted_uses:
        raise SovereigntyDenied("source use not permitted")
    customer = record.source_class in {SourceClass.CUSTOMER, SourceClass.CUSTOMER_DERIVED}
    if customer and (
        tenant_id != record.tenant_id
        or use in {PermittedUse.SHARED_RETRIEVAL, PermittedUse.GLOBAL_LEARNING}
    ):
        # Opt-in global generalization requires a distinct, reviewed, source-neutral
        # contribution; this contract never releases customer/derived payloads.
        raise SovereigntyDenied("customer intelligence cannot cross tenant boundary")
    if use in {PermittedUse.GLOBAL_LEARNING, PermittedUse.EXPORT, PermittedUse.EVALUATION}:
        if not record.reviewer_ref:
            raise SovereigntyDenied("reviewed use authorization required")
    for parent_id in sorted(record.parent_source_ids):
        authorize_source_use(
            parent_id,
            records=records,
            use=use,
            tenant_id=tenant_id,
            at=at,
            _ancestors=_ancestors | {source_id},
        )

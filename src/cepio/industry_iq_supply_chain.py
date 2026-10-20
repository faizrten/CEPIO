from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field


_SHA256_DIGEST = re.compile(r"^sha256:[0-9a-fA-F]{64}$")

SupplyChainVerification = Literal["host_verified", "unverified"]
SignatureKind = Literal["sigstore", "x509", "pgp", "other"]
SBOMFormat = Literal["spdx", "cyclonedx", "other"]
VulnerabilitySeverity = Literal["none", "low", "medium", "high", "critical", "unknown"]

_SEVERITY_RANK: dict[VulnerabilitySeverity, int] = {
    "none": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
    "unknown": 99,
}


def _default_sbom_formats() -> set[SBOMFormat]:
    return {"spdx", "cyclonedx"}


class IndustryIQSupplyChainError(ValueError):
    """Fail-closed supply-chain evidence or policy failure."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class IndustryIQPublisherAttestation(BaseModel):
    """Host-verified signed publisher attestation bound to one artifact digest.

    CEPIO Core does not perform signature verification. A source adapter or deployment
    host verifies the signature and records the verification result here. ``signature_ref``
    points to the external signature/attestation evidence, not to secret key material.
    """

    subject_digest: str = Field(min_length=1)
    publisher: str = Field(min_length=1)
    signer_identity: str = Field(min_length=1)
    signature_kind: SignatureKind
    signature_ref: str = Field(min_length=1)
    predicate_type: str = Field(min_length=1)
    verification: SupplyChainVerification = "unverified"


class IndustryIQSBOMEvidence(BaseModel):
    """Host-verified SBOM evidence for one pack artifact."""

    subject_digest: str = Field(min_length=1)
    document_digest: str = Field(min_length=1)
    format: SBOMFormat
    source_ref: str = Field(min_length=1)
    verification: SupplyChainVerification = "unverified"


class IndustryIQVulnerabilityScan(BaseModel):
    """Host-verified vulnerability result bound to an artifact and optional SBOM."""

    subject_digest: str = Field(min_length=1)
    sbom_document_digest: str | None = None
    scanner: str = Field(min_length=1)
    scanner_version: str | None = None
    source_ref: str = Field(min_length=1)
    highest_severity: VulnerabilitySeverity
    verification: SupplyChainVerification = "unverified"


class IndustryIQSupplyChainEvidence(BaseModel):
    """Supply-chain evidence bundle retained with catalogue provenance."""

    publisher_attestation: IndustryIQPublisherAttestation | None = None
    sbom: IndustryIQSBOMEvidence | None = None
    vulnerability_scan: IndustryIQVulnerabilityScan | None = None


class IndustryIQSupplyChainPolicy(BaseModel):
    """Host-controlled policy for signed provenance, SBOM, and vulnerability evidence.

    Defaults preserve v0.6 admission behavior. Hosts can opt into strict external-pack
    qualification with ``strict_external``; future remote source adapters should use
    that mode rather than weakening the catalogue boundary.
    """

    require_publisher_attestation_for_external: bool = False
    require_sbom_for_external: bool = False
    require_vulnerability_scan_for_external: bool = False
    trusted_signing_identities: set[str] = Field(default_factory=set)
    allowed_attestation_predicate_types: set[str] = Field(default_factory=set)
    allowed_sbom_formats: set[SBOMFormat] = Field(default_factory=_default_sbom_formats)
    maximum_vulnerability_severity: VulnerabilitySeverity | None = None

    @classmethod
    def strict_external(
        cls,
        *,
        trusted_signing_identities: set[str] | None = None,
        allowed_attestation_predicate_types: set[str] | None = None,
        allowed_sbom_formats: set[SBOMFormat] | None = None,
        maximum_vulnerability_severity: VulnerabilitySeverity | None = None,
    ) -> IndustryIQSupplyChainPolicy:
        return cls(
            require_publisher_attestation_for_external=True,
            require_sbom_for_external=True,
            require_vulnerability_scan_for_external=True,
            trusted_signing_identities=set(trusted_signing_identities or set()),
            allowed_attestation_predicate_types=set(allowed_attestation_predicate_types or set()),
            allowed_sbom_formats=set(allowed_sbom_formats or {"spdx", "cyclonedx"}),
            maximum_vulnerability_severity=maximum_vulnerability_severity,
        )

    def enforce(
        self,
        *,
        artifact_digest: str | None,
        publisher: str | None,
        external: bool,
        evidence: IndustryIQSupplyChainEvidence | None,
    ) -> None:
        requires_any = external and (
            self.require_publisher_attestation_for_external
            or self.require_sbom_for_external
            or self.require_vulnerability_scan_for_external
        )
        if requires_any and artifact_digest is None:
            raise IndustryIQSupplyChainError(
                "PACK_SUPPLY_CHAIN_DIGEST_REQUIRED",
                "Supply-chain qualification requires an artifact digest.",
            )

        attestation = evidence.publisher_attestation if evidence is not None else None
        sbom = evidence.sbom if evidence is not None else None
        scan = evidence.vulnerability_scan if evidence is not None else None

        if external and self.require_publisher_attestation_for_external and attestation is None:
            raise IndustryIQSupplyChainError(
                "PACK_PUBLISHER_ATTESTATION_REQUIRED",
                "External Industry IQ pack requires a signed publisher attestation.",
            )
        if external and self.require_sbom_for_external and sbom is None:
            raise IndustryIQSupplyChainError(
                "PACK_SBOM_REQUIRED",
                "External Industry IQ pack requires host-verified SBOM evidence.",
            )
        if external and self.require_vulnerability_scan_for_external and scan is None:
            raise IndustryIQSupplyChainError(
                "PACK_VULNERABILITY_SCAN_REQUIRED",
                "External Industry IQ pack requires a host-verified vulnerability scan.",
            )

        if attestation is not None:
            self._enforce_attestation(
                attestation, artifact_digest=artifact_digest, publisher=publisher
            )
        if sbom is not None:
            self._enforce_sbom(sbom, artifact_digest=artifact_digest)
        if scan is not None:
            self._enforce_scan(scan, artifact_digest=artifact_digest, sbom=sbom)

    def _enforce_attestation(
        self,
        attestation: IndustryIQPublisherAttestation,
        *,
        artifact_digest: str | None,
        publisher: str | None,
    ) -> None:
        _require_sha256(attestation.subject_digest, "PACK_ATTESTATION_SUBJECT_DIGEST_INVALID")
        if attestation.verification != "host_verified":
            raise IndustryIQSupplyChainError(
                "PACK_PUBLISHER_ATTESTATION_UNVERIFIED",
                "Publisher attestation signature was not host-verified.",
            )
        if artifact_digest is None or attestation.subject_digest != artifact_digest:
            raise IndustryIQSupplyChainError(
                "PACK_PUBLISHER_ATTESTATION_DIGEST_MISMATCH",
                "Publisher attestation subject digest does not match the pack artifact digest.",
            )
        if publisher is None or attestation.publisher != publisher:
            raise IndustryIQSupplyChainError(
                "PACK_PUBLISHER_ATTESTATION_IDENTITY_MISMATCH",
                "Publisher attestation identity does not match catalogue provenance.",
            )
        if (
            self.trusted_signing_identities
            and attestation.signer_identity not in self.trusted_signing_identities
        ):
            raise IndustryIQSupplyChainError(
                "PACK_SIGNER_UNTRUSTED",
                f"Publisher attestation signer is not trusted: {attestation.signer_identity}",
            )
        if (
            self.allowed_attestation_predicate_types
            and attestation.predicate_type not in self.allowed_attestation_predicate_types
        ):
            raise IndustryIQSupplyChainError(
                "PACK_ATTESTATION_PREDICATE_NOT_ALLOWED",
                f"Publisher attestation predicate is not allowed: {attestation.predicate_type}",
            )

    def _enforce_sbom(
        self,
        sbom: IndustryIQSBOMEvidence,
        *,
        artifact_digest: str | None,
    ) -> None:
        _require_sha256(sbom.subject_digest, "PACK_SBOM_SUBJECT_DIGEST_INVALID")
        _require_sha256(sbom.document_digest, "PACK_SBOM_DOCUMENT_DIGEST_INVALID")
        if sbom.verification != "host_verified":
            raise IndustryIQSupplyChainError(
                "PACK_SBOM_UNVERIFIED",
                "SBOM evidence was not host-verified.",
            )
        if artifact_digest is None or sbom.subject_digest != artifact_digest:
            raise IndustryIQSupplyChainError(
                "PACK_SBOM_DIGEST_MISMATCH",
                "SBOM subject digest does not match the pack artifact digest.",
            )
        if self.allowed_sbom_formats and sbom.format not in self.allowed_sbom_formats:
            raise IndustryIQSupplyChainError(
                "PACK_SBOM_FORMAT_NOT_ALLOWED",
                f"SBOM format is not allowed: {sbom.format}",
            )

    def _enforce_scan(
        self,
        scan: IndustryIQVulnerabilityScan,
        *,
        artifact_digest: str | None,
        sbom: IndustryIQSBOMEvidence | None,
    ) -> None:
        _require_sha256(scan.subject_digest, "PACK_VULNERABILITY_SUBJECT_DIGEST_INVALID")
        if scan.sbom_document_digest is not None:
            _require_sha256(
                scan.sbom_document_digest,
                "PACK_VULNERABILITY_SBOM_DIGEST_INVALID",
            )
        if scan.verification != "host_verified":
            raise IndustryIQSupplyChainError(
                "PACK_VULNERABILITY_SCAN_UNVERIFIED",
                "Vulnerability scan was not host-verified.",
            )
        if artifact_digest is None or scan.subject_digest != artifact_digest:
            raise IndustryIQSupplyChainError(
                "PACK_VULNERABILITY_DIGEST_MISMATCH",
                "Vulnerability scan subject digest does not match the pack artifact digest.",
            )
        if sbom is not None and scan.sbom_document_digest != sbom.document_digest:
            raise IndustryIQSupplyChainError(
                "PACK_VULNERABILITY_SBOM_MISMATCH",
                "Vulnerability scan is not bound to the admitted SBOM document digest.",
            )
        maximum = self.maximum_vulnerability_severity
        if maximum is not None and _SEVERITY_RANK[scan.highest_severity] > _SEVERITY_RANK[maximum]:
            raise IndustryIQSupplyChainError(
                "PACK_VULNERABILITY_POLICY_VIOLATION",
                (
                    "Vulnerability severity exceeds policy: "
                    f"observed={scan.highest_severity}, maximum={maximum}."
                ),
            )


def _require_sha256(value: str, code: str) -> None:
    if not _SHA256_DIGEST.fullmatch(value):
        raise IndustryIQSupplyChainError(
            code,
            "Supply-chain digest must use sha256:<64 hex characters>.",
        )

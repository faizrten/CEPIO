from __future__ import annotations

import pytest

from cepio.bootstrap import build_runtime
from cepio.drilling_npt_iq import DRILLING_NPT_IQ_PACK
from cepio.industry_iq_catalogue import (
    IndustryIQCatalogue,
    IndustryIQCatalogueCandidate,
    IndustryIQCatalogueError,
    IndustryIQPackProvenance,
    IndustryIQTrustPolicy,
)
from cepio.industry_iq_supply_chain import (
    IndustryIQPublisherAttestation,
    IndustryIQSBOMEvidence,
    IndustryIQSupplyChainEvidence,
    IndustryIQSupplyChainPolicy,
    IndustryIQVulnerabilityScan,
)


ARTIFACT_DIGEST = "sha256:" + "a" * 64
OTHER_DIGEST = "sha256:" + "b" * 64
SBOM_DIGEST = "sha256:" + "c" * 64
OTHER_SBOM_DIGEST = "sha256:" + "d" * 64
PREDICATE = "https://slsa.dev/provenance/v1"
SIGNER = "https://github.com/faizrten/CEPIO/.github/workflows/release.yml@refs/heads/main"


class StaticSource:
    source_id = "repo:industry-iq"

    def __init__(self, provenance: IndustryIQPackProvenance) -> None:
        self._provenance = provenance

    def discover(self):
        return [IndustryIQCatalogueCandidate(DRILLING_NPT_IQ_PACK, self._provenance)]


def attestation(**updates) -> IndustryIQPublisherAttestation:
    values = {
        "subject_digest": ARTIFACT_DIGEST,
        "publisher": "cepio",
        "signer_identity": SIGNER,
        "signature_kind": "sigstore",
        "signature_ref": "oci://registry.example/cepio.iq.drilling.npt:0.1.0.sig",
        "predicate_type": PREDICATE,
        "verification": "host_verified",
    }
    values.update(updates)
    return IndustryIQPublisherAttestation(**values)


def sbom(**updates) -> IndustryIQSBOMEvidence:
    values = {
        "subject_digest": ARTIFACT_DIGEST,
        "document_digest": SBOM_DIGEST,
        "format": "cyclonedx",
        "source_ref": "oci://registry.example/cepio.iq.drilling.npt:0.1.0.sbom",
        "verification": "host_verified",
    }
    values.update(updates)
    return IndustryIQSBOMEvidence(**values)


def scan(**updates) -> IndustryIQVulnerabilityScan:
    values = {
        "subject_digest": ARTIFACT_DIGEST,
        "sbom_document_digest": SBOM_DIGEST,
        "scanner": "example-scanner",
        "scanner_version": "1.0.0",
        "source_ref": "oci://registry.example/cepio.iq.drilling.npt:0.1.0.scan",
        "highest_severity": "low",
        "verification": "host_verified",
    }
    values.update(updates)
    return IndustryIQVulnerabilityScan(**values)


def evidence(
    *,
    publisher_attestation: IndustryIQPublisherAttestation | None = None,
    sbom_evidence: IndustryIQSBOMEvidence | None = None,
    vulnerability_scan: IndustryIQVulnerabilityScan | None = None,
) -> IndustryIQSupplyChainEvidence:
    return IndustryIQSupplyChainEvidence(
        publisher_attestation=publisher_attestation or attestation(),
        sbom=sbom_evidence or sbom(),
        vulnerability_scan=vulnerability_scan or scan(),
    )


def provenance(
    *,
    artifact_digest: str | None = ARTIFACT_DIGEST,
    publisher: str | None = "cepio",
    supply_chain: IndustryIQSupplyChainEvidence | None = None,
) -> IndustryIQPackProvenance:
    return IndustryIQPackProvenance(
        source_id="repo:industry-iq",
        source_kind="repository",
        source_ref="github:faizrten/industry-iq@deadbeef",
        publisher=publisher,
        artifact_digest=artifact_digest,
        verification="host_verified",
        supply_chain=supply_chain,
    )


def strict_policy(**updates) -> IndustryIQTrustPolicy:
    supply_chain_values = {
        "trusted_signing_identities": {SIGNER},
        "allowed_attestation_predicate_types": {PREDICATE},
        "allowed_sbom_formats": {"cyclonedx"},
        "maximum_vulnerability_severity": "medium",
    }
    supply_chain_values.update(updates)
    return IndustryIQTrustPolicy(
        trusted_source_ids={"repo:industry-iq"},
        trusted_publishers={"cepio"},
        supply_chain_policy=IndustryIQSupplyChainPolicy.strict_external(**supply_chain_values),
    )


def ingest_one(
    pack_provenance: IndustryIQPackProvenance,
    *,
    policy: IndustryIQTrustPolicy | None = None,
) -> IndustryIQCatalogue:
    catalogue = IndustryIQCatalogue(policy or strict_policy(), core_version="0.4.0")
    catalogue.ingest(StaticSource(pack_provenance))
    return catalogue


def assert_rejected(
    code: str,
    pack_provenance: IndustryIQPackProvenance,
    *,
    policy: IndustryIQTrustPolicy | None = None,
) -> None:
    catalogue = IndustryIQCatalogue(policy or strict_policy(), core_version="0.4.0")
    with pytest.raises(IndustryIQCatalogueError) as exc:
        catalogue.ingest(StaticSource(pack_provenance))
    assert exc.value.code == code
    assert catalogue.records() == []


def test_strict_supply_chain_admission_preserves_evidence_in_deployment():
    chain = evidence()
    catalogue = ingest_one(provenance(supply_chain=chain))
    runtime = build_runtime()

    result = catalogue.install(runtime, {"cepio.iq.drilling.npt": "==0.1.0"})

    recorded = result.provenance["cepio.iq.drilling.npt"]
    assert recorded.supply_chain == chain
    assert recorded.supply_chain.publisher_attestation.signer_identity == SIGNER
    assert recorded.supply_chain.sbom.document_digest == SBOM_DIGEST
    assert recorded.supply_chain.vulnerability_scan.highest_severity == "low"


def test_default_v06_policy_remains_backward_compatible_without_supply_chain_evidence():
    policy = IndustryIQTrustPolicy(
        trusted_source_ids={"repo:industry-iq"},
        trusted_publishers={"cepio"},
    )

    catalogue = ingest_one(provenance(supply_chain=None), policy=policy)

    assert len(catalogue.records()) == 1
    assert catalogue.records()[0].provenance.supply_chain is None


@pytest.mark.parametrize(
    ("chain", "expected_code"),
    [
        (
            IndustryIQSupplyChainEvidence(sbom=sbom(), vulnerability_scan=scan()),
            "PACK_PUBLISHER_ATTESTATION_REQUIRED",
        ),
        (
            IndustryIQSupplyChainEvidence(
                publisher_attestation=attestation(), vulnerability_scan=scan()
            ),
            "PACK_SBOM_REQUIRED",
        ),
        (
            IndustryIQSupplyChainEvidence(publisher_attestation=attestation(), sbom=sbom()),
            "PACK_VULNERABILITY_SCAN_REQUIRED",
        ),
    ],
)
def test_strict_policy_requires_all_supply_chain_evidence(chain, expected_code):
    assert_rejected(expected_code, provenance(supply_chain=chain))


def test_strict_policy_requires_artifact_digest_even_if_legacy_digest_requirement_disabled():
    policy = strict_policy()
    policy.require_digest_for_external = False

    assert_rejected(
        "PACK_SUPPLY_CHAIN_DIGEST_REQUIRED",
        provenance(artifact_digest=None, supply_chain=evidence()),
        policy=policy,
    )


@pytest.mark.parametrize(
    ("publisher_attestation", "expected_code"),
    [
        (attestation(verification="unverified"), "PACK_PUBLISHER_ATTESTATION_UNVERIFIED"),
        (
            attestation(subject_digest="sha256:not-valid"),
            "PACK_ATTESTATION_SUBJECT_DIGEST_INVALID",
        ),
        (
            attestation(subject_digest=OTHER_DIGEST),
            "PACK_PUBLISHER_ATTESTATION_DIGEST_MISMATCH",
        ),
        (
            attestation(publisher="other"),
            "PACK_PUBLISHER_ATTESTATION_IDENTITY_MISMATCH",
        ),
        (
            attestation(signer_identity="https://example.invalid/untrusted"),
            "PACK_SIGNER_UNTRUSTED",
        ),
        (
            attestation(predicate_type="https://example.invalid/predicate"),
            "PACK_ATTESTATION_PREDICATE_NOT_ALLOWED",
        ),
    ],
)
def test_publisher_attestation_fails_closed(publisher_attestation, expected_code):
    chain = evidence(publisher_attestation=publisher_attestation)
    assert_rejected(expected_code, provenance(supply_chain=chain))


def test_publisher_attestation_requires_catalogue_publisher_identity():
    policy = strict_policy()
    policy.trusted_publishers = set()
    assert_rejected(
        "PACK_PUBLISHER_ATTESTATION_IDENTITY_MISMATCH",
        provenance(publisher=None, supply_chain=evidence()),
        policy=policy,
    )


@pytest.mark.parametrize(
    ("sbom_evidence", "expected_code"),
    [
        (
            sbom(subject_digest="sha256:not-valid"),
            "PACK_SBOM_SUBJECT_DIGEST_INVALID",
        ),
        (
            sbom(document_digest="sha256:not-valid"),
            "PACK_SBOM_DOCUMENT_DIGEST_INVALID",
        ),
        (sbom(verification="unverified"), "PACK_SBOM_UNVERIFIED"),
        (sbom(subject_digest=OTHER_DIGEST), "PACK_SBOM_DIGEST_MISMATCH"),
        (sbom(format="spdx"), "PACK_SBOM_FORMAT_NOT_ALLOWED"),
    ],
)
def test_sbom_evidence_fails_closed(sbom_evidence, expected_code):
    chain = evidence(sbom_evidence=sbom_evidence)
    assert_rejected(expected_code, provenance(supply_chain=chain))


@pytest.mark.parametrize(
    ("vulnerability_scan", "expected_code"),
    [
        (
            scan(subject_digest="sha256:not-valid"),
            "PACK_VULNERABILITY_SUBJECT_DIGEST_INVALID",
        ),
        (
            scan(sbom_document_digest="sha256:not-valid"),
            "PACK_VULNERABILITY_SBOM_DIGEST_INVALID",
        ),
        (scan(verification="unverified"), "PACK_VULNERABILITY_SCAN_UNVERIFIED"),
        (scan(subject_digest=OTHER_DIGEST), "PACK_VULNERABILITY_DIGEST_MISMATCH"),
        (
            scan(sbom_document_digest=OTHER_SBOM_DIGEST),
            "PACK_VULNERABILITY_SBOM_MISMATCH",
        ),
        (scan(highest_severity="critical"), "PACK_VULNERABILITY_POLICY_VIOLATION"),
        (scan(highest_severity="unknown"), "PACK_VULNERABILITY_POLICY_VIOLATION"),
    ],
)
def test_vulnerability_evidence_fails_closed(vulnerability_scan, expected_code):
    chain = evidence(vulnerability_scan=vulnerability_scan)
    assert_rejected(expected_code, provenance(supply_chain=chain))


def test_optional_scan_without_sbom_can_still_be_digest_validated_under_non_strict_policy():
    policy = IndustryIQTrustPolicy(
        trusted_source_ids={"repo:industry-iq"},
        trusted_publishers={"cepio"},
        supply_chain_policy=IndustryIQSupplyChainPolicy(
            require_vulnerability_scan_for_external=True,
            maximum_vulnerability_severity="high",
        ),
    )
    chain = IndustryIQSupplyChainEvidence(
        vulnerability_scan=scan(sbom_document_digest=None, highest_severity="medium")
    )

    catalogue = ingest_one(provenance(supply_chain=chain), policy=policy)

    assert len(catalogue.records()) == 1

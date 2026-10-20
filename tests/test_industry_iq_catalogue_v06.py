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


DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


class StaticSource:
    def __init__(self, source_id: str, candidates: list[IndustryIQCatalogueCandidate]) -> None:
        self.source_id = source_id
        self._candidates = candidates

    def discover(self):
        return list(self._candidates)


def provenance(
    *,
    source_id: str = "repo:industry-iq",
    digest: str | None = DIGEST_A,
    publisher: str | None = "cepio",
    verification: str = "host_verified",
):
    return IndustryIQPackProvenance(
        source_id=source_id,
        source_kind="repository",
        source_ref="github:faizrten/industry-iq@deadbeef",
        publisher=publisher,
        artifact_digest=digest,
        verification=verification,
    )


def trusted_policy() -> IndustryIQTrustPolicy:
    return IndustryIQTrustPolicy(
        trusted_source_ids={"repo:industry-iq"},
        trusted_publishers={"cepio"},
    )


def test_trusted_catalogue_installs_pack_and_preserves_provenance_in_deployment_evidence():
    catalogue = IndustryIQCatalogue(trusted_policy(), core_version="0.4.0")
    catalogue.ingest(
        StaticSource(
            "repo:industry-iq",
            [IndustryIQCatalogueCandidate(DRILLING_NPT_IQ_PACK, provenance())],
        )
    )
    runtime = build_runtime()

    result = catalogue.install(runtime, {"cepio.iq.drilling.npt": "==0.1.0"})

    assert runtime.industry_iq_packs == {"cepio.iq.drilling.npt": "0.1.0"}
    assert result.deployment.install_order == ["cepio.iq.drilling.npt"]
    recorded = result.provenance["cepio.iq.drilling.npt"]
    assert recorded.source_id == "repo:industry-iq"
    assert recorded.artifact_digest == DIGEST_A
    assert runtime.industry_iq_catalogue_deployment == result


def test_unverified_candidate_fails_closed_and_batch_is_not_partially_admitted():
    catalogue = IndustryIQCatalogue(trusted_policy(), core_version="0.4.0")
    good = IndustryIQCatalogueCandidate(DRILLING_NPT_IQ_PACK, provenance())
    bad = IndustryIQCatalogueCandidate(
        DRILLING_NPT_IQ_PACK,
        provenance(verification="unverified"),
    )

    with pytest.raises(IndustryIQCatalogueError) as exc:
        catalogue.ingest(StaticSource("repo:industry-iq", [good, bad]))

    assert exc.value.code == "PACK_PROVENANCE_UNVERIFIED"
    assert catalogue.records() == []


def test_untrusted_source_and_publisher_fail_closed():
    catalogue = IndustryIQCatalogue(trusted_policy(), core_version="0.4.0")

    with pytest.raises(IndustryIQCatalogueError) as source_exc:
        catalogue.ingest(
            StaticSource(
                "repo:untrusted",
                [
                    IndustryIQCatalogueCandidate(
                        DRILLING_NPT_IQ_PACK,
                        provenance(source_id="repo:untrusted"),
                    )
                ],
            )
        )
    assert source_exc.value.code == "PACK_SOURCE_UNTRUSTED"

    with pytest.raises(IndustryIQCatalogueError) as publisher_exc:
        catalogue.ingest(
            StaticSource(
                "repo:industry-iq",
                [
                    IndustryIQCatalogueCandidate(
                        DRILLING_NPT_IQ_PACK,
                        provenance(publisher="unknown"),
                    )
                ],
            )
        )
    assert publisher_exc.value.code == "PACK_PUBLISHER_UNTRUSTED"


def test_external_candidate_requires_valid_sha256_digest():
    catalogue = IndustryIQCatalogue(trusted_policy(), core_version="0.4.0")

    with pytest.raises(IndustryIQCatalogueError) as missing_exc:
        catalogue.ingest(
            StaticSource(
                "repo:industry-iq",
                [IndustryIQCatalogueCandidate(DRILLING_NPT_IQ_PACK, provenance(digest=None))],
            )
        )
    assert missing_exc.value.code == "PACK_DIGEST_REQUIRED"

    with pytest.raises(IndustryIQCatalogueError) as invalid_exc:
        catalogue.ingest(
            StaticSource(
                "repo:industry-iq",
                [
                    IndustryIQCatalogueCandidate(
                        DRILLING_NPT_IQ_PACK,
                        provenance(digest="sha256:not-a-digest"),
                    )
                ],
            )
        )
    assert invalid_exc.value.code == "PACK_DIGEST_INVALID"


def test_source_adapter_cannot_spoof_another_trusted_source_identity():
    policy = IndustryIQTrustPolicy(
        trusted_source_ids={"repo:industry-iq", "repo:mirror"},
        trusted_publishers={"cepio"},
    )
    catalogue = IndustryIQCatalogue(policy, core_version="0.4.0")

    with pytest.raises(IndustryIQCatalogueError) as exc:
        catalogue.ingest(
            StaticSource(
                "repo:mirror",
                [IndustryIQCatalogueCandidate(DRILLING_NPT_IQ_PACK, provenance())],
            )
        )

    assert exc.value.code == "CATALOGUE_SOURCE_MISMATCH"
    assert catalogue.records() == []


def test_same_pack_version_with_conflicting_provenance_is_rejected():
    catalogue = IndustryIQCatalogue(trusted_policy(), core_version="0.4.0")
    catalogue.ingest(
        StaticSource(
            "repo:industry-iq",
            [IndustryIQCatalogueCandidate(DRILLING_NPT_IQ_PACK, provenance(digest=DIGEST_A))],
        )
    )

    with pytest.raises(IndustryIQCatalogueError) as exc:
        catalogue.ingest(
            StaticSource(
                "repo:industry-iq",
                [IndustryIQCatalogueCandidate(DRILLING_NPT_IQ_PACK, provenance(digest=DIGEST_B))],
            )
        )

    assert exc.value.code == "CATALOGUE_PACK_PROVENANCE_CONFLICT"
    assert len(catalogue.records()) == 1
    assert catalogue.records()[0].provenance.artifact_digest == DIGEST_A


def test_empty_catalogue_source_id_fails_closed_before_discovery():
    catalogue = IndustryIQCatalogue(trusted_policy(), core_version="0.4.0")

    with pytest.raises(IndustryIQCatalogueError) as exc:
        catalogue.ingest(StaticSource("", []))

    assert exc.value.code == "CATALOGUE_SOURCE_ID_INVALID"
    assert catalogue.records() == []


def test_builtin_verification_cannot_be_claimed_by_external_source():
    catalogue = IndustryIQCatalogue(trusted_policy(), core_version="0.4.0")
    candidate = IndustryIQCatalogueCandidate(
        DRILLING_NPT_IQ_PACK,
        provenance(verification="builtin"),
    )

    with pytest.raises(IndustryIQCatalogueError) as exc:
        catalogue.ingest(StaticSource("repo:industry-iq", [candidate]))

    assert exc.value.code == "PACK_PROVENANCE_INVALID"
    assert catalogue.records() == []


def test_identical_pack_and_provenance_cannot_be_silently_readmitted():
    catalogue = IndustryIQCatalogue(trusted_policy(), core_version="0.4.0")
    candidate = IndustryIQCatalogueCandidate(DRILLING_NPT_IQ_PACK, provenance())
    source = StaticSource("repo:industry-iq", [candidate])
    catalogue.ingest(source)

    with pytest.raises(IndustryIQCatalogueError) as exc:
        catalogue.ingest(source)

    assert exc.value.code == "CATALOGUE_PACK_ALREADY_PRESENT"
    assert len(catalogue.records()) == 1

"""Offline ACCC admission tests; no model, network, source or Action execution."""

import pytest

from cepio.accc_readonly import (
    CompositionPlan,
    CompositionRequest,
    CompositionStatus,
    ReadOnlyComposer,
    TrustedAdmission,
    HostBoundComposer,
)
from cepio.capability_registry import (
    CapabilityLayer,
    CapabilityMaturity,
    CapabilityProvenance,
    CapabilityRecord,
    CapabilityRegistry,
)


def composer(maturity=CapabilityMaturity.QUALIFIED):
    cap = CapabilityRecord(
        id="k201",
        version="0.1",
        title="K201 vibration",
        description="reliability",
        layer=CapabilityLayer.DOMAIN,
        maturity=maturity,
        validated_domains={"reliability"},
        skills={"inspect-vibration"},
        evidence_requirements={"vibration-observation"},
        provenance=CapabilityProvenance(mode="synthetic"),
    )
    return ReadOnlyComposer(CapabilityRegistry(id="test", version="1", capabilities=[cap]))


def admission(**kwargs):
    values = dict(
        actor_id="engineer",
        tenant_id="tenant-a",
        authorization_valid=True,
        approved_capability_ids={"k201"},
        ready_skill_ids={"inspect-vibration"},
        verified_evidence_types={"vibration-observation"},
    )
    values.update(kwargs)
    return TrustedAdmission(**values)


def request():
    return CompositionRequest(
        query_text="K201 vibration reliability",
        domain="reliability",
        required_capability_ids={"k201"},
    )


def test_admissible_plan_is_read_only():
    result = composer().compose(request(), admission())
    assert result.status == CompositionStatus.READY
    assert result.capability_ids == ["k201"]
    assert result.read_only and not result.external_action_executed


def test_missing_evidence_requires_more_evidence():
    result = composer().compose(request(), admission(verified_evidence_types=set()))
    assert result.status == CompositionStatus.NEEDS_EVIDENCE
    assert "vibration-observation" in result.missing_evidence
    assert not result.capability_ids


def test_unverified_host_identity_blocks():
    result = composer().compose(request(), admission(authorization_valid=False))
    assert result.status == CompositionStatus.BLOCKED


def test_preflight_not_ready_blocks():
    result = composer().compose(request(), admission(ready_skill_ids=set()))
    assert "SKILL_PREFLIGHT_NOT_READY" in result.blockers


def test_unqualified_capability_blocks():
    result = composer(CapabilityMaturity.EXPERIMENTAL).compose(request(), admission())
    assert "CAPABILITY_NOT_QUALIFIED" in result.blockers


def test_invalid_domain_blocks():
    req = request().model_copy(update={"domain": "reservoir"})
    result = composer().compose(req, admission())
    assert "DOMAIN_NOT_VALIDATED" in result.blockers


def test_conflicting_sources_block():
    result = composer().compose(request(), admission(source_conflicts=True))
    assert "SOURCE_CONFLICT" in result.blockers


def test_incompatible_method_blocks():
    result = composer().compose(request(), admission(incompatible_capability_ids={"k201"}))
    assert "METHOD_INCOMPATIBLE" in result.blockers


def test_unknown_required_capability_blocks():
    req = request().model_copy(update={"required_capability_ids": {"not-registered"}})
    result = composer().compose(req, admission())
    assert "REQUIRED_CAPABILITY_UNKNOWN" in result.blockers


def test_unapproved_capability_blocks():
    result = composer().compose(request(), admission(approved_capability_ids=set()))
    assert "CAPABILITY_NOT_HOST_APPROVED" in result.blockers


def test_host_bound_composer_resolves_admission_without_client_supplied_authority():
    host = HostBoundComposer(composer(), lambda req: admission())
    result = host.compose(request())
    assert result.status == CompositionStatus.READY
    assert result.manifest_hash
    assert result.manifest_hash == host.compose(request()).manifest_hash


def test_host_bound_composer_fails_closed_when_resolver_unavailable():
    host = HostBoundComposer(composer(), lambda req: None)
    result = host.compose(request())
    assert result.status == CompositionStatus.BLOCKED
    assert result.blockers == ["HOST_ADMISSION_UNAVAILABLE"]


def test_required_capability_does_not_admit_lexical_neighbor():
    from cepio.capability_registry import CapabilityRecord, CapabilityRegistry

    neighbor = CapabilityRecord(
        id="neighbor",
        version="0.1",
        title="K201 vibration neighbor",
        description="reliability",
        layer=CapabilityLayer.DOMAIN,
        maturity=CapabilityMaturity.QUALIFIED,
        validated_domains={"reliability"},
        provenance=CapabilityProvenance(mode="synthetic"),
    )
    original = composer().registry.capabilities[0]
    candidate = ReadOnlyComposer(
        CapabilityRegistry(
            id="test",
            version="1",
            capabilities=[original, neighbor],
        )
    )
    result = candidate.compose(request(), admission())
    assert result.status == CompositionStatus.READY
    assert result.capability_ids == ["k201"]


def test_profile_capability_cannot_be_admitted_by_offline_stub():
    profile = CapabilityRecord(
        id="k201",
        version="0.1",
        title="K201 vibration",
        description="reliability",
        layer=CapabilityLayer.PROFILE,
        maturity=CapabilityMaturity.QUALIFIED,
        validated_domains={"reliability"},
        skills={"inspect-vibration"},
        evidence_requirements={"vibration-observation"},
        provenance=CapabilityProvenance(mode="synthetic"),
    )
    candidate = ReadOnlyComposer(
        CapabilityRegistry(
            id="test",
            version="1",
            capabilities=[profile],
        )
    )
    result = candidate.compose(request(), admission())
    assert result.status == CompositionStatus.BLOCKED
    assert "PROFILE_CAPABILITY_NOT_SUPPORTED" in result.blockers


def test_plan_denies_capabilities_and_skills_while_blocked():
    with pytest.raises(ValueError, match="non-ready plan"):
        CompositionPlan(
            status=CompositionStatus.BLOCKED,
            skill_ids=["inspect-vibration"],
        )


def test_plan_denies_ready_status_with_unresolved_evidence():
    with pytest.raises(ValueError, match="ready plan"):
        CompositionPlan(
            status=CompositionStatus.READY,
            missing_evidence=["vibration-observation"],
        )


def test_registry_removed_capability_is_not_admitted(monkeypatch):
    candidate = composer()
    monkeypatch.setattr(type(candidate.registry), "get", lambda self, _id: None)
    result = candidate.compose(request(), admission())
    assert result.status == CompositionStatus.BLOCKED
    assert "CAPABILITY_NOT_REGISTERED" in result.blockers
    assert "REQUIRED_CAPABILITY_NOT_SELECTED" in result.blockers
    assert "NO_ELIGIBLE_CAPABILITY" in result.blockers

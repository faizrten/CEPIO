"""Offline tests of the host-owned ACCC admission resolver."""
from dataclasses import dataclass

import pytest

from cepio.accc_host_admission import (
    EvidenceVerification, HostPrincipal, RuntimeAdmissionResolver,
)
from cepio.accc_readonly import CompositionRequest, CompositionStatus, HostBoundComposer, ReadOnlyComposer
from cepio.capability_registry import (
    CapabilityLayer, CapabilityMaturity, CapabilityProvenance,
    CapabilityRecord, CapabilityRegistry,
)


def registry():
    record = CapabilityRecord(
        id="k201", version="0.1", title="K201", description="reliability",
        layer=CapabilityLayer.DOMAIN, maturity=CapabilityMaturity.QUALIFIED,
        validated_domains={"reliability"}, skills={"inspect"},
        evidence_requirements={"vibration"},
        provenance=CapabilityProvenance(mode="synthetic"),
    )
    return CapabilityRegistry(id="test", version="1", capabilities=[record])


@dataclass
class Preflight:
    status: str


class Skills:
    def __init__(self, status="READY"):
        self.status = status
        self.calls = []

    def preflight(self, skill_id, *, actor_id, actor_roles):
        self.calls.append((skill_id, actor_id, actor_roles))
        return Preflight(self.status)


class Services:
    def __init__(self, verified=True):
        self.verified = verified

    def authenticated_principal(self):
        return HostPrincipal("engineer", "tenant-a", frozenset({"reliability"}))

    def verify_evidence(self, request, principal):
        return EvidenceVerification(self.verified, frozenset({"vibration"}))

    def eligible_capabilities(self, request, principal):
        return {"k201"}

    def incompatible_capabilities(self, request, principal):
        return set()


def request():
    return CompositionRequest(query_text="K201 vibration", domain="reliability")


def test_real_preflight_receipt_is_used():
    skills = Skills()
    admission = RuntimeAdmissionResolver(registry(), skills, Services())(request())
    assert admission.ready_skill_ids == {"inspect"}
    assert skills.calls == [("inspect", "engineer", {"reliability"})]
    assert admission.tenant_id == "tenant-a"


def test_blocked_preflight_never_becomes_ready():
    admission = RuntimeAdmissionResolver(registry(), Skills("BLOCKED"), Services())(request())
    assert admission.ready_skill_ids == set()


def test_unverified_evidence_fails_closed():
    with pytest.raises(PermissionError):
        RuntimeAdmissionResolver(registry(), Skills(), Services(False))(request())


def test_host_failure_returns_blocked_plan():
    host = HostBoundComposer(ReadOnlyComposer(registry()),
                             RuntimeAdmissionResolver(registry(), Skills(), Services(False)))
    plan = host.compose(request())
    assert plan.status == CompositionStatus.BLOCKED
    assert plan.blockers == ["HOST_ADMISSION_UNAVAILABLE"]
    assert plan.capability_ids == []


def test_host_ready_skill_is_necessary_for_plan():
    host = HostBoundComposer(ReadOnlyComposer(registry()),
                             RuntimeAdmissionResolver(registry(), Skills("BLOCKED"), Services()))
    plan = host.compose(request())
    assert plan.status == CompositionStatus.BLOCKED
    assert "SKILL_PREFLIGHT_NOT_READY" in plan.blockers


def test_host_valid_admission_returns_plan_only():
    host = HostBoundComposer(ReadOnlyComposer(registry()),
                             RuntimeAdmissionResolver(registry(), Skills(), Services()))
    plan = host.compose(request())
    assert plan.status == CompositionStatus.READY
    assert plan.read_only and not plan.external_action_executed


def test_missing_authenticated_principal_fails_closed():
    class MissingPrincipal(Services):
        def authenticated_principal(self):
            return None

    with pytest.raises(PermissionError):
        RuntimeAdmissionResolver(registry(), Skills(), MissingPrincipal())(request())


def test_unavailable_capability_eligibility_fails_closed():
    class MissingEligibility(Services):
        def eligible_capabilities(self, request, principal):
            return None

    with pytest.raises(PermissionError):
        RuntimeAdmissionResolver(registry(), Skills(), MissingEligibility())(request())


def test_skill_preflight_exception_does_not_grant_readiness():
    class MissingSkill(Skills):
        def preflight(self, skill_id, *, actor_id, actor_roles):
            raise KeyError(skill_id)

    result = RuntimeAdmissionResolver(registry(), MissingSkill(), Services())(request())
    assert result.ready_skill_ids == set()

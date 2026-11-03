"""Offline tests of the host-owned ACCC admission resolver."""
from dataclasses import dataclass

import pytest

from cepio.accc_host_admission import (
    EvidenceVerification, HostPrincipal, RuntimeAdmissionResolver,
)
from cepio.accc_readonly import CompositionRequest
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

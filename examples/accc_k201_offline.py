"""Synthetic mechanics-only K-201 composition. No industrial uplift claim.

Run: PYTHONPATH=src python examples/accc_k201_offline.py
"""

from datetime import datetime, timezone
import json

from cepio.accc_readonly import CompositionRequest
from cepio.accc_runtime_binding import (
    AdmissionProfile,
    AuthenticatedReadOnlyComposer,
    EvidenceRequirement,
    contract_hash,
)
from cepio.auth import ActorContext
from cepio.capability_registry import CapabilityRecord, CapabilityRegistry
from cepio.domain_bindings import ExternalRecordReference
from cepio.model import OntologyObject
from cepio.platform_bindings import (
    BindingRegistration,
    EvidenceEnvelope,
    PlatformBindingManifest,
)
from cepio.policy import RolePolicyEngine
from cepio.registry import TypeRegistry
from cepio.runtime import CEPIORuntime
from cepio.skill_preflight import SkillPreflightSpec, SkillRegistry


AT = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
ASSET = "urn:synthetic:Asset"


class OfflineEvidence:
    manifest = PlatformBindingManifest(
        binding_id="offline-evidence",
        provider_id="synthetic",
        source_system="fixture",
        mode="evidence",
        capabilities={"resolve-evidence", "versioned-identity"},
    )

    def __init__(self):
        self.calls = 0
        self.record = EvidenceEnvelope(
            reference=ExternalRecordReference(
                source_system="fixture",
                record_kind="vibration",
                record_id="observation-1",
                record_version="1",
            ),
            evidence={
                "tenant_id": "synthetic",
                "subject_id": "K-201",
                "evidence_type": "vibration",
                "observed_at": AT.isoformat(),
                "conflict": False,
                "payload_hash": "synthetic-no-industrial-measurement",
            },
        )

    def resolve_evidence(self, external_id):
        self.calls += 1
        if external_id != "observation-1":
            raise KeyError(external_id)
        return self.record.model_copy(deep=True)


def build_demo():
    runtime = CEPIORuntime(
        type_registry=TypeRegistry(object_type_ids={ASSET}),
        policy_engine=RolePolicyEngine(
            {
                "engineer": {
                    "read_types": [ASSET, "vibration"],
                    "functions": ["cepio.compose_readonly"],
                }
            }
        ),
    )
    runtime.upsert_object(OntologyObject(id="K-201", type=ASSET, name="Synthetic K-201"))
    skills = SkillRegistry(runtime)
    spec = SkillPreflightSpec(skill_id="inspect", object_types={"asset": ASSET})
    skills.register(spec)
    capability = CapabilityRecord(
        id="synthetic-k201",
        version="0.1",
        title="K-201 composition fixture",
        description="Synthetic plumbing qualification only",
        layer="DOMAIN",
        maturity="QUALIFIED",
        validated_domains={"reliability"},
        skills={"inspect"},
        evidence_requirements={"vibration"},
        provenance={"mode": "synthetic"},
    )
    registry = CapabilityRegistry(id="offline", version="1", capabilities=[capability])
    binding = OfflineEvidence()
    profile = AdmissionProfile(
        tenant_id="synthetic",
        subject_id="K-201",
        domain="reliability",
        policy_version="1",
        capability_hashes={capability.id: contract_hash(capability)},
        skill_hashes={spec.skill_id: contract_hash(spec)},
        compatible_sets=frozenset({frozenset({capability.id})}),
        evidence=(EvidenceRequirement("observation-1", "vibration", 60),),
    )
    host = AuthenticatedReadOnlyComposer(
        registry,
        skills,
        lambda: ActorContext("offline-engineer", {"engineer"}, "synthetic"),
        binding,
        BindingRegistration(manifest=binding.manifest, capability_id=capability.id),
        profile,
        lambda: AT,
    )
    request = CompositionRequest(
        query_text="Inspect synthetic K-201",
        domain="reliability",
        subject_id="K-201",
        required_capability_ids={capability.id},
    )
    return host, request


def main():
    host, request = build_demo()
    ready = host.compose(request)
    assert ready.status == "READY"
    assert ready == host.compose(request)
    host.binding.record.evidence["conflict"] = True
    blocked = host.compose(request)
    assert blocked.status == "BLOCKED"
    print(
        json.dumps(
            {
                "qualification": "synthetic mechanics only; no source attestation or Industry IQ uplift",
                "ready": ready.model_dump(mode="json"),
                "abstention": blocked.model_dump(mode="json"),
            },
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

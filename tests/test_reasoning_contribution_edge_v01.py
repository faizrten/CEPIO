from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cepio.application_contract import CEPIOApplicationService, EvidenceRole, ExecutionContext
from cepio.bootstrap import build_runtime
from cepio.industry_iq import install_industry_iq_packs
from cepio.model import ObjectRef, OntologyObject
from cepio.performance_contract import (
    PerformanceContract,
    PerformanceNode,
    PerformanceSubject,
    PerformanceTarget,
)
from cepio.performance_industry_iq import (
    PERFORMANCE_RESPONSE_IQ_PACK,
    PerformanceReasoningError,
    PerformanceReasoningRequest,
    build_performance_industry_iq_service_with_reasoning,
)
from cepio.performance_registry import InMemoryPerformanceContractStore, PerformanceContractRegistry
from cepio.performance_runtime import PerformanceObservation
from cepio.performance_service import PerformanceService
from cepio.reasoning_contribution import BoundedReasoningHost, ReasoningContributionRequest
from cepio.reliability_reasoning import ReliabilityReasoningContributor


NOW = datetime(2026, 10, 19, 14, 30, tzinfo=timezone.utc)


def reasoning_request(objects: tuple[OntologyObject, ...]) -> ReasoningContributionRequest:
    return ReasoningContributionRequest(
        subject=ObjectRef(id="COMP-EDGE", type="Equipment"),
        problem="Investigate compressor availability deviation",
        performance_node_id="availability",
        performance_status="off_track",
        performance_evidence_refs=("pi://availability/COMP-EDGE",),
        context_object_refs=tuple(ObjectRef(id=obj.id, type=obj.type) for obj in objects),
    )


def test_reliability_handles_count_conflict_recurrence_and_confidence_edges():
    context = (
        OntologyObject(
            id="COND-SEVERITY",
            type="ConditionObservation",
            name="Bearing condition",
            properties={"severity": "high"},
        ),
        OntologyObject(
            id="FAIL-A",
            type="FailureEvent",
            name="Seal failure",
            properties={"failure_mode": "seal"},
        ),
        OntologyObject(
            id="FAIL-B",
            type="FailureEvent",
            name="Coupling failure",
            properties={"failure_mode": "coupling"},
        ),
        OntologyObject(
            id="WO-BOOL",
            type="WorkOrder",
            name="Boolean reopen count must not be numeric",
            properties={"status": "planned", "reopen_count": True},
        ),
        OntologyObject(
            id="WO-FLOAT",
            type="WorkOrder",
            name="Float reopen count",
            properties={"status": "planned", "reopen_count": 2.0},
        ),
        OntologyObject(
            id="WO-CONFLICT",
            type="WorkOrder",
            name="Reopened but verified work",
            properties={
                "status": "reopened",
                "reopen_count": 1,
                "verification_status": "verified",
            },
        ),
    )
    contribution = ReliabilityReasoningContributor().contribute(
        reasoning_request(context),
        BoundedReasoningHost(context),
    )

    condition = next(
        item for item in contribution.hypotheses if item.id == "reliability.condition-degradation"
    )
    assert condition.confidence.value == "medium"
    condition_evidence = next(
        item for item in contribution.evidence if item.id == "reliability.condition:COND-SEVERITY"
    )
    assert "severity=high" in condition_evidence.summary

    recurrence = next(
        item
        for item in contribution.hypotheses
        if item.id == "reliability.recurring-failure-mechanism"
    )
    assert recurrence.supporting_evidence_ids == (
        "reliability.failure:FAIL-A",
        "reliability.failure:FAIL-B",
    )

    bool_work = next(
        item for item in contribution.evidence if item.id == "reliability.work:WO-BOOL"
    )
    assert "reopen_count=" not in bool_work.summary
    float_work = next(
        item for item in contribution.evidence if item.id == "reliability.work:WO-FLOAT"
    )
    assert "reopen_count=2" in float_work.summary
    conflict_work = next(
        item for item in contribution.evidence if item.id == "reliability.work:WO-CONFLICT"
    )
    assert conflict_work.reference.role == EvidenceRole.contextual

    corrective = next(
        item
        for item in contribution.hypotheses
        if item.id == "reliability.corrective-action-effectiveness"
    )
    assert corrective.confidence.value == "low"

    two_abnormal = (
        OntologyObject(
            id="COND-A",
            type="ConditionSignal",
            name="Vibration A",
            properties={"status": "degraded"},
        ),
        OntologyObject(
            id="COND-B",
            type="ConditionSignal",
            name="Vibration B",
            properties={"trend": "worsening"},
        ),
    )
    high_confidence = ReliabilityReasoningContributor().contribute(
        reasoning_request(two_abnormal),
        BoundedReasoningHost(two_abnormal),
    )
    condition_high = next(
        item
        for item in high_confidence.hypotheses
        if item.id == "reliability.condition-degradation"
    )
    assert condition_high.confidence.value == "high"


@pytest.mark.parametrize("reopen_count", [None, "2", 1.5, -1, -2.0, True])
def test_reliability_ignores_invalid_or_negative_reopen_counts(reopen_count: object):
    context = (
        OntologyObject(
            id="WO-INVALID",
            type="WorkOrder",
            name="Work without a valid reopen count",
            properties={"status": "planned", "reopen_count": reopen_count},
        ),
    )

    contribution = ReliabilityReasoningContributor().contribute(
        reasoning_request(context),
        BoundedReasoningHost(context),
    )

    assert len(contribution.evidence) == 1
    assert contribution.evidence[0].reference.role == EvidenceRole.contextual
    assert "reopen_count=" not in contribution.evidence[0].summary
    assert contribution.hypotheses == ()


def test_performance_reasoning_translates_missing_domain_pack_fail_closed():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="COMP-EDGE",
            type="Equipment",
            name="Edge Compressor",
            properties={"sharingScope": "internal"},
        )
    )
    runtime.upsert_object(
        OntologyObject(
            id="WO-EDGE",
            type="WorkOrder",
            name="Edge work order",
            properties={"sharingScope": "internal"},
        )
    )
    install_industry_iq_packs(runtime, [PERFORMANCE_RESPONSE_IQ_PACK])

    contract = PerformanceContract(
        id="org-edge-performance",
        version="1.0.0",
        name="Edge performance",
        layer="organization",
        organization_id="org-edge",
        subjects=(PerformanceSubject(id="operations", kind="function", name="Operations"),),
        nodes=(
            PerformanceNode(
                id="availability",
                kind="kpi",
                name="Operational availability",
                scope_subject_id="operations",
                target=PerformanceTarget(operator="gte", value=0.95),
            ),
        ),
    )
    registry = PerformanceContractRegistry(InMemoryPerformanceContractStore())
    registry.register(contract, activate=True, created_at=NOW)
    service = build_performance_industry_iq_service_with_reasoning(
        PerformanceService(registry),
        CEPIOApplicationService(runtime),
        reasoning_contributors=(ReliabilityReasoningContributor(),),
    )
    request = PerformanceReasoningRequest(
        contract_id=contract.id,
        node_id="availability",
        subject=ObjectRef(id="COMP-EDGE", type="Equipment"),
        observations=(
            PerformanceObservation(
                node_id="availability",
                value=0.90,
                observed_at=NOW,
                evidence_refs=("pi://availability/COMP-EDGE",),
                source_subject_id="COMP-EDGE",
            ),
        ),
        evaluated_at=NOW,
        context_object_ids=("WO-EDGE",),
    )
    context = ExecutionContext(
        actor_id="industry-iq-agent",
        actor_roles=frozenset({"cepio_admin"}),
        tenant_id="org-edge",
    )

    with pytest.raises(PerformanceReasoningError) as exc_info:
        service.reason(request, context)

    assert exc_info.value.code == "REASONING_PACK_NOT_INSTALLED"

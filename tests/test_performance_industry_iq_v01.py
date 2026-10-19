from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cepio.application_contract import CEPIOApplicationService, ExecutionContext
from cepio.bootstrap import build_runtime
from cepio.industry_iq import install_industry_iq_packs
from cepio.model import ObjectRef, OntologyObject
from cepio.performance_contract import (
    PerformanceContract,
    PerformanceContribution,
    PerformanceNode,
    PerformanceResponseBinding,
    PerformanceSubject,
    PerformanceTarget,
)
from cepio.performance_industry_iq import (
    PERFORMANCE_RESPONSE_DECISION_TYPE,
    PERFORMANCE_RESPONSE_IQ_PACK,
    PerformanceIndustryIQService,
    PerformanceReasoningError,
    PerformanceReasoningRequest,
)
from cepio.performance_registry import InMemoryPerformanceContractStore, PerformanceContractRegistry
from cepio.performance_runtime import PerformanceObservation
from cepio.performance_service import PerformanceService
from cepio.runtime import AuthorizationError


NOW = datetime(2026, 10, 19, 13, 30, tzinfo=timezone.utc)


def performance_contract() -> PerformanceContract:
    return PerformanceContract(
        id="org-a-performance",
        version="1.0.0",
        name="Org A operating performance",
        layer="organization",
        organization_id="org-a",
        subjects=(
            PerformanceSubject(
                id="operations",
                kind="function",
                name="Operations",
            ),
        ),
        nodes=(
            PerformanceNode(
                id="repeat-failures",
                kind="key_result",
                name="Repeat compressor failures",
                scope_subject_id="operations",
                unit="count",
                target=PerformanceTarget(operator="lte", value=1.0),
            ),
            PerformanceNode(
                id="maintenance-cost",
                kind="metric",
                name="Maintenance cost index",
                scope_subject_id="operations",
                unit="index",
                target=PerformanceTarget(operator="lte", value=100.0),
            ),
            PerformanceNode(
                id="availability",
                kind="kpi",
                name="Operational availability",
                scope_subject_id="operations",
                unit="ratio",
                target=PerformanceTarget(operator="gte", value=0.95),
            ),
        ),
        contributions=(
            PerformanceContribution(
                source_node_id="repeat-failures",
                target_node_id="availability",
                relation="contributes_to",
                rationale="Repeat failures structurally threaten availability",
            ),
            PerformanceContribution(
                source_node_id="maintenance-cost",
                target_node_id="availability",
                relation="influences",
                rationale="Cost pressure may influence maintenance choices",
            ),
        ),
        response_bindings=(
            PerformanceResponseBinding(
                id="availability-investigation",
                node_id="availability",
                statuses=frozenset({"at_risk", "off_track", "critical"}),
                workflow_definition_id="investigate-availability-loss",
                rationale="Investigate material availability deviation",
            ),
        ),
    )


def observations(*, include_availability: bool = True) -> tuple[PerformanceObservation, ...]:
    values = [
        PerformanceObservation(
            node_id="repeat-failures",
            value=3.0,
            observed_at=NOW,
            evidence_refs=("cmms://failures/C-4102/2026-10-19",),
            source_subject_id="COMP-1",
        ),
        PerformanceObservation(
            node_id="maintenance-cost",
            value=120.0,
            observed_at=NOW,
            evidence_refs=("erp://maintenance-cost/C-4102/2026-10-19",),
            source_subject_id="COMP-1",
        ),
    ]
    if include_availability:
        values.append(
            PerformanceObservation(
                node_id="availability",
                value=0.90,
                observed_at=NOW,
                evidence_refs=("pi://availability/C-4102/2026-10-19",),
                source_subject_id="COMP-1",
            )
        )
    return tuple(values)


def build_services(*, install_pack: bool = True):
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="COMP-1",
            type="Equipment",
            name="Compressor C-4102",
            properties={"sharingScope": "internal"},
        )
    )
    runtime.upsert_object(
        OntologyObject(
            id="COMP-2",
            type="Equipment",
            name="Compressor C-4103",
            properties={"sharingScope": "internal"},
        )
    )
    runtime.upsert_object(
        OntologyObject(
            id="WO-1",
            type="WorkOrder",
            name="Inspect C-4102",
            properties={"sharingScope": "internal"},
        )
    )
    if install_pack:
        install_industry_iq_packs(runtime, [PERFORMANCE_RESPONSE_IQ_PACK])

    registry = PerformanceContractRegistry(InMemoryPerformanceContractStore())
    registry.register(performance_contract(), activate=True, created_at=NOW)
    performance_service = PerformanceService(registry)
    application_service = CEPIOApplicationService(runtime)
    return runtime, PerformanceIndustryIQService(performance_service, application_service)


def admin_context(*, tenant_id: str = "org-a") -> ExecutionContext:
    return ExecutionContext(
        actor_id="industry-iq-agent",
        actor_roles=frozenset({"cepio_admin"}),
        tenant_id=tenant_id,
        correlation_id="corr-performance-1",
    )


def request(*, subject_id: str = "COMP-1", include_availability: bool = True):
    return PerformanceReasoningRequest(
        contract_id="org-a-performance",
        node_id="availability",
        subject=ObjectRef(id=subject_id, type="Equipment"),
        observations=observations(include_availability=include_availability),
        evaluated_at=NOW,
        context_object_ids=("WO-1", "WO-1"),
    )


def test_reasoning_creates_explainable_recommend_only_decision_proposal():
    _, service = build_services()

    assessment = service.reason(request(), admin_context())

    assert assessment.contract_version == "1.0.0"
    assert assessment.organization_id == "org-a"
    assert assessment.node_name == "Operational availability"
    assert assessment.subject == ObjectRef(id="COMP-1", type="Equipment")
    assert assessment.deviation.source_subject_id == "COMP-1"
    assert assessment.deviation.risk_sources == ("repeat-failures",)
    assert assessment.deviation.influence_sources == ("maintenance-cost",)
    assert assessment.contextual_objects == (ObjectRef(id="WO-1", type="WorkOrder"),)
    assert assessment.workflow_candidates[0].workflow_definition_id == (
        "investigate-availability-loss"
    )
    assert assessment.workflow_candidates[0].authority == "recommend_only"
    assert assessment.decision_proposal.decision_type == PERFORMANCE_RESPONSE_DECISION_TYPE
    assert assessment.decision_proposal.recommended_action is None
    assert "do not treat it as causal proof" in assessment.decision_proposal.recommendation
    assert "no workflow has been started" in assessment.decision_proposal.recommendation
    assert any("Upstream structural risk sources" in item for item in assessment.decision_proposal.observations)
    assert any("Influence context (not causal proof)" in item for item in assessment.decision_proposal.observations)
    assert assessment.authority == "recommend_only"
    assert assessment.policy_required is True
    assert assessment.causal_claim_made is False


def test_explicit_proposal_persists_governed_decision_without_execution():
    runtime, service = build_services()

    result = service.propose_decision(request(), admin_context())

    assert result.decision.decision_type == PERFORMANCE_RESPONSE_DECISION_TYPE
    assert result.decision.created_by == "industry-iq-agent"
    assert result.decision.subject.id == "COMP-1"
    assert result.decision.recommended_action is None
    assert result.authority == "recommend_only"
    assert result.workflow_started is False
    assert result.action_executed is False
    assert runtime.get_decision(result.decision.id).id == result.decision.id
    assert runtime.all_audits() == []


def test_reasoning_fails_closed_across_tenant_boundary():
    _, service = build_services()

    with pytest.raises(PerformanceReasoningError) as exc_info:
        service.reason(request(), admin_context(tenant_id="org-b"))

    assert exc_info.value.code == "ORGANIZATION_SCOPE_MISMATCH"


def test_reasoning_requires_source_subject_to_match_decision_subject():
    _, service = build_services()

    with pytest.raises(PerformanceReasoningError) as exc_info:
        service.reason(request(subject_id="COMP-2"), admin_context())

    assert exc_info.value.code == "SOURCE_SUBJECT_MISMATCH"


def test_propagated_at_risk_state_without_direct_source_subject_cannot_become_decision():
    _, service = build_services()

    with pytest.raises(PerformanceReasoningError) as exc_info:
        service.reason(request(include_availability=False), admin_context())

    assert exc_info.value.code == "SOURCE_SUBJECT_REQUIRED"


def test_decision_persistence_still_obeys_actor_policy():
    _, service = build_services()
    auditor = ExecutionContext(
        actor_id="auditor-1",
        actor_roles=frozenset({"auditor"}),
        tenant_id="org-a",
    )

    assessment = service.reason(request(), auditor)
    assert assessment.decision_proposal.decision_type == PERFORMANCE_RESPONSE_DECISION_TYPE

    with pytest.raises(AuthorizationError):
        service.propose_decision(request(), auditor)


def test_reasoning_requires_deployed_industry_iq_capability():
    _, service = build_services(install_pack=False)

    with pytest.raises(PerformanceReasoningError) as exc_info:
        service.reason(request(), admin_context())

    assert exc_info.value.code == "PERFORMANCE_IQ_PACK_NOT_INSTALLED"

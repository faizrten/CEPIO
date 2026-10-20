from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from cepio.performance_contract import (
    PerformanceAccountability,
    PerformanceContract,
    PerformanceContribution,
    PerformanceNode,
    PerformanceResponseBinding,
    PerformanceStatus,
    PerformanceSubject,
    PerformanceTarget,
    PerformanceThreshold,
)
from cepio.performance_runtime import PerformanceObservation, PerformanceRuntime


def refinery_contract() -> PerformanceContract:
    return PerformanceContract(
        id="refinery-performance",
        version="0.1.0",
        name="Refinery enterprise performance graph",
        layer="organization",
        organization_id="refinery-co",
        subjects=(
            PerformanceSubject(id="refinery-co", kind="enterprise", name="Refinery Co"),
            PerformanceSubject(
                id="operations", kind="function", name="Operations", parent_id="refinery-co"
            ),
            PerformanceSubject(
                id="coo", kind="role", name="Chief Operating Officer", parent_id="operations"
            ),
            PerformanceSubject(
                id="reliability-engineer",
                kind="persona",
                name="Reliability Engineer",
                parent_id="operations",
            ),
            PerformanceSubject(
                id="engineer-42",
                kind="individual",
                name="Engineer 42",
                parent_id="reliability-engineer",
            ),
        ),
        nodes=(
            PerformanceNode(
                id="profitability",
                kind="objective",
                name="Improve refinery profitability",
                scope_subject_id="refinery-co",
            ),
            PerformanceNode(
                id="availability",
                kind="kpi",
                name="Operational availability",
                scope_subject_id="coo",
                unit="ratio",
                definition="Organization-specific operational availability definition",
                formula_ref="logic://refinery-co/availability/v7",
                reference_node_id="cepio.reference.refinery.operational-availability",
                target=PerformanceTarget(operator="gte", value=0.96),
                thresholds=(
                    PerformanceThreshold(
                        status="critical",
                        condition=PerformanceTarget(operator="lte", value=0.90),
                        reason="Availability is below the critical operating threshold",
                    ),
                ),
            ),
            PerformanceNode(
                id="repeat-failures",
                kind="key_result",
                name="Reduce repeat compressor failures",
                scope_subject_id="engineer-42",
                target=PerformanceTarget(operator="lte", value=5),
            ),
            PerformanceNode(
                id="maintenance-cost",
                kind="guardrail",
                name="Maintenance cost guardrail",
                scope_subject_id="operations",
                target=PerformanceTarget(operator="lte", value=100),
            ),
        ),
        accountabilities=(
            PerformanceAccountability(
                subject_id="coo", node_id="availability", relation="accountable_for"
            ),
            PerformanceAccountability(
                subject_id="engineer-42", node_id="repeat-failures", relation="owns"
            ),
        ),
        contributions=(
            PerformanceContribution(
                source_node_id="repeat-failures",
                target_node_id="availability",
                relation="contributes_to",
                rationale="Repeat failures reduce operational availability",
            ),
            PerformanceContribution(
                source_node_id="availability",
                target_node_id="profitability",
                relation="contributes_to",
            ),
            PerformanceContribution(
                source_node_id="maintenance-cost",
                target_node_id="profitability",
                relation="constrains",
            ),
        ),
        response_bindings=(
            PerformanceResponseBinding(
                id="availability-investigation",
                node_id="availability",
                statuses=frozenset({"off_track", "critical"}),
                workflow_definition_id="investigate-availability-loss",
                rationale="Investigate material availability deviation",
            ),
        ),
    )


def test_contract_models_organization_persona_and_individual_accountability():
    contract = refinery_contract()

    subjects = {subject.id: subject for subject in contract.subjects}
    assert subjects["coo"].kind.value == "role"
    assert subjects["reliability-engineer"].kind.value == "persona"
    assert subjects["engineer-42"].kind.value == "individual"
    assert contract.nodes[1].reference_node_id == (
        "cepio.reference.refinery.operational-availability"
    )
    assert contract.nodes[1].formula_ref == "logic://refinery-co/availability/v7"


def test_runtime_links_individual_kr_to_enterprise_risk_without_overwriting_direct_kpi():
    now = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)
    result = PerformanceRuntime().evaluate(
        refinery_contract(),
        (
            PerformanceObservation(
                node_id="availability",
                value=0.92,
                observed_at=now,
                evidence_refs=("pi://unit-4/availability/2026-10-19",),
            ),
            PerformanceObservation(
                node_id="repeat-failures",
                value=9,
                observed_at=now,
                evidence_refs=("sap://failure-history/k201",),
                source_subject_id="engineer-42",
            ),
            PerformanceObservation(
                node_id="maintenance-cost",
                value=90,
                observed_at=now,
                evidence_refs=("erp://maintenance-cost/october",),
            ),
        ),
        evaluated_at=now,
    )

    availability = result.node("availability")
    profitability = result.node("profitability")

    assert availability.status == PerformanceStatus.off_track
    assert availability.risk_sources == ("repeat-failures",)
    assert profitability.status == PerformanceStatus.at_risk
    assert profitability.risk_sources == ("availability",)

    assert len(result.workflow_candidates) == 1
    candidate = result.workflow_candidates[0]
    assert candidate.workflow_definition_id == "investigate-availability-loss"
    assert candidate.authority == "recommend_only"
    assert candidate.policy_required is True


def test_threshold_can_escalate_target_miss_to_critical():
    now = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)
    result = PerformanceRuntime().evaluate(
        refinery_contract(),
        (
            PerformanceObservation(
                node_id="availability",
                value=0.88,
                observed_at=now,
                evidence_refs=("pi://unit-4/availability/critical",),
            ),
        ),
        evaluated_at=now,
    )

    assert result.node("availability").status == PerformanceStatus.critical
    assert result.workflow_candidates[0].source_status == PerformanceStatus.critical


def test_stale_or_missing_observation_fails_closed_to_unknown():
    now = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)
    contract = PerformanceContract(
        id="freshness",
        version="0.1.0",
        name="Freshness",
        layer="organization",
        subjects=(PerformanceSubject(id="org", kind="enterprise", name="Org"),),
        nodes=(
            PerformanceNode(
                id="kpi",
                kind="kpi",
                name="KPI",
                scope_subject_id="org",
                target=PerformanceTarget(operator="gte", value=1),
                max_observation_age_seconds=60,
            ),
        ),
    )

    stale = PerformanceRuntime().evaluate(
        contract,
        (
            PerformanceObservation(
                node_id="kpi",
                value=2,
                observed_at=now - timedelta(seconds=61),
                evidence_refs=("source://stale",),
            ),
        ),
        evaluated_at=now,
    )
    missing = PerformanceRuntime().evaluate(contract, (), evaluated_at=now)

    assert stale.node("kpi").status == PerformanceStatus.unknown
    assert "stale" in stale.node("kpi").reasons[0].lower()
    assert missing.node("kpi").status == PerformanceStatus.unknown


def test_observation_requires_evidence_and_timezone_aware_time():
    now = datetime(2026, 10, 19, 10, 0)
    with pytest.raises(ValidationError):
        PerformanceObservation(
            node_id="availability", value=0.95, observed_at=now, evidence_refs=()
        )

    with pytest.raises(ValueError, match="timezone-aware"):
        PerformanceRuntime().evaluate(
            refinery_contract(),
            (
                PerformanceObservation(
                    node_id="availability",
                    value=0.95,
                    observed_at=now,
                    evidence_refs=("pi://availability",),
                ),
            ),
            evaluated_at=datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc),
        )


def test_influence_is_visible_but_does_not_assert_causal_risk():
    now = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)
    contract = PerformanceContract(
        id="influence",
        version="0.1.0",
        name="Influence",
        layer="organization",
        subjects=(PerformanceSubject(id="org", kind="enterprise", name="Org"),),
        nodes=(
            PerformanceNode(
                id="market-price",
                kind="metric",
                name="Market price",
                scope_subject_id="org",
                target=PerformanceTarget(operator="gte", value=80),
            ),
            PerformanceNode(
                id="margin",
                kind="kpi",
                name="Margin",
                scope_subject_id="org",
            ),
        ),
        contributions=(
            PerformanceContribution(
                source_node_id="market-price",
                target_node_id="margin",
                relation="influences",
            ),
        ),
    )

    result = PerformanceRuntime().evaluate(
        contract,
        (
            PerformanceObservation(
                node_id="market-price",
                value=70,
                observed_at=now,
                evidence_refs=("market://price",),
            ),
        ),
        evaluated_at=now,
    )

    assert result.node("market-price").status == PerformanceStatus.off_track
    assert result.node("margin").status == PerformanceStatus.unknown
    assert result.node("margin").risk_sources == ()
    assert result.node("margin").influence_sources == ("market-price",)


def test_contract_rejects_structural_cycles_and_dangling_references():
    subject = PerformanceSubject(id="org", kind="enterprise", name="Org")
    nodes = (
        PerformanceNode(id="a", kind="kpi", name="A", scope_subject_id="org"),
        PerformanceNode(id="b", kind="kpi", name="B", scope_subject_id="org"),
    )

    with pytest.raises(ValidationError, match="acyclic"):
        PerformanceContract(
            id="cycle",
            version="0.1.0",
            name="Cycle",
            layer="organization",
            subjects=(subject,),
            nodes=nodes,
            contributions=(
                PerformanceContribution(
                    source_node_id="a", target_node_id="b", relation="contributes_to"
                ),
                PerformanceContribution(
                    source_node_id="b", target_node_id="a", relation="depends_on"
                ),
            ),
        )

    with pytest.raises(ValidationError, match="unknown accountability node"):
        PerformanceContract(
            id="dangling",
            version="0.1.0",
            name="Dangling",
            layer="organization",
            subjects=(subject,),
            nodes=nodes,
            accountabilities=(
                PerformanceAccountability(
                    subject_id="org", node_id="missing", relation="accountable_for"
                ),
            ),
        )

"""Acceptance tests for synthetic Rig 07 Performance Pack activation."""

from __future__ import annotations

from datetime import timedelta

import pytest

from cepio.industry_performance_packs import drilling_contractor_performance_pack
from cepio.performance_business_logic import (
    BusinessLogicExecutionError,
    BusinessLogicInput,
)
from cepio.performance_runtime import PerformanceStatus
from scripts.drilling_performance_activation_v01 import (
    CONTRACT_ID,
    EVALUATED_AT,
    KR,
    LEAKAGE,
    NPT,
    OBJECTIVE,
    ORG,
    RIG_MANAGER,
    SAFETY,
    UPTIME,
    WELL_CONTROL,
    _trusted_logic,
    organization_overlay,
    run_activation,
)


def test_rig07_activation_uses_reference_inheritance_and_tenant_provenance():
    reference = drilling_contractor_performance_pack()
    result = run_activation()
    contract = result.resolution.resolved.contract

    assert contract.organization_id == ORG
    assert result.assessment.contract_id == CONTRACT_ID
    assert result.resolution.resolved.source_contract_ids == (
        reference.id,
        CONTRACT_ID,
    )
    assert len(result.assessment.source_revision_hashes) == 2
    assert all(result.assessment.source_revision_hashes)
    assert result.resolution.resolved.source_for("node", NPT).source_contract_id == CONTRACT_ID
    assert next(node for node in reference.nodes if node.id == NPT).formula_ref is None
    assert next(node for node in contract.nodes if node.id == NPT).target.value == 0.08
    assert any(
        item.subject_id == RIG_MANAGER
        and item.node_id == UPTIME
        and item.relation.value == "accountable_for"
        for item in contract.accountabilities
    )
    assert not any(
        item.subject_id == "drilling.reference.rig-manager" and item.node_id == UPTIME
        for item in contract.accountabilities
    )


def test_rig07_npt_and_okr_are_evaluated_without_imputed_causes():
    result = run_activation()
    evaluation = result.assessment.evaluation

    assert evaluation.node(NPT).value == pytest.approx(0.10)
    assert evaluation.node(NPT).status == PerformanceStatus.off_track
    assert evaluation.node(KR).value == pytest.approx(0.10)
    assert evaluation.node(KR).status == PerformanceStatus.off_track
    assert evaluation.node(UPTIME).value == pytest.approx(0.90)
    assert evaluation.node(UPTIME).status == PerformanceStatus.off_track
    assert evaluation.node(OBJECTIVE).status == PerformanceStatus.at_risk
    assert KR in evaluation.node(OBJECTIVE).risk_sources

    npt = evaluation.node(NPT)
    assert "synthetic://rig07/npt-event-ledger" in npt.evidence_refs
    assert "synthetic://rig07/eligible-clock" in npt.evidence_refs
    assert all(execution.definition_hash for execution in result.business_logic_executions)


def test_financial_exposure_needs_approved_contract_evidence():
    observed = run_activation()
    assert observed.assessment.evaluation.node(LEAKAGE).value == 32000.0
    assert observed.assessment.evaluation.node(LEAKAGE).status == PerformanceStatus.off_track
    assert any(
        "contract-confirmed-nonbillable-hours" in reference
        for reference in observed.assessment.evaluation.node(LEAKAGE).evidence_refs
    )

    missing = run_activation(include_financial_evidence=False)
    financial = missing.assessment.evaluation.node(LEAKAGE)
    assert financial.value is None
    assert financial.status == PerformanceStatus.unknown
    assert all(
        execution.formula_ref != "logic://synthetic-rigco/rig07/revenue-leakage/v1"
        for execution in missing.business_logic_executions
    )


def test_guardrails_require_evidence_and_do_not_default_to_green():
    observed = run_activation().assessment.evaluation
    assert observed.node(SAFETY).status == PerformanceStatus.on_track
    assert observed.node(WELL_CONTROL).status == PerformanceStatus.on_track

    missing = run_activation(include_guardrail_evidence=False).assessment.evaluation
    assert missing.node(SAFETY).status == PerformanceStatus.unknown
    assert missing.node(WELL_CONTROL).status == PerformanceStatus.unknown


def test_governed_response_is_recommend_only_without_external_side_effect():
    result = run_activation()
    candidates = result.assessment.workflow_candidates
    assert len(candidates) == 1
    assert candidates[0].source_node_id == NPT
    assert candidates[0].workflow_definition_id == "drilling-rig07-reliability-investigation"
    assert candidates[0].authority == "recommend_only"
    assert candidates[0].policy_required is True
    assert result.assessment.authority == "recommend_only"
    assert result.assessment.policy_required is True


def test_business_logic_rejects_stale_and_unauthorized_inputs():
    result = run_activation()
    contract = result.resolution.resolved.contract
    logic = _trusted_logic()

    with pytest.raises(BusinessLogicExecutionError) as error:
        logic.materialize(
            contract,
            NPT,
            (
                BusinessLogicInput(
                    name="classified_npt_hours",
                    value=12.0,
                    observed_at=EVALUATED_AT - timedelta(days=2),
                    evidence_refs=("synthetic://rig07/old-event",),
                ),
                BusinessLogicInput(
                    name="eligible_hours",
                    value=120.0,
                    observed_at=EVALUATED_AT,
                    evidence_refs=("synthetic://rig07/clock",),
                ),
            ),
            evaluated_at=EVALUATED_AT,
        )
    assert error.value.code == "STALE_INPUT"

    other_org = contract.model_copy(update={"organization_id": "other-tenant"})
    with pytest.raises(BusinessLogicExecutionError) as error:
        logic.materialize(
            other_org,
            NPT,
            (
                BusinessLogicInput(
                    name="classified_npt_hours",
                    value=12.0,
                    observed_at=EVALUATED_AT,
                    evidence_refs=("synthetic://rig07/npt",),
                ),
                BusinessLogicInput(
                    name="eligible_hours",
                    value=120.0,
                    observed_at=EVALUATED_AT,
                    evidence_refs=("synthetic://rig07/clock",),
                ),
            ),
            evaluated_at=EVALUATED_AT,
        )
    assert error.value.code == "ORGANIZATION_SCOPE_MISMATCH"


def test_invalid_denominator_is_rejected_not_guessed():
    contract = run_activation().resolution.resolved.contract
    with pytest.raises(BusinessLogicExecutionError) as error:
        _trusted_logic().materialize(
            contract,
            NPT,
            (
                BusinessLogicInput(
                    name="classified_npt_hours",
                    value=12.0,
                    observed_at=EVALUATED_AT,
                    evidence_refs=("synthetic://rig07/npt",),
                ),
                BusinessLogicInput(
                    name="eligible_hours",
                    value=0.0,
                    observed_at=EVALUATED_AT,
                    evidence_refs=("synthetic://rig07/clock",),
                ),
            ),
            evaluated_at=EVALUATED_AT,
        )
    assert error.value.code == "FUNCTION_EXECUTION_FAILED"


def test_overlay_remains_synthetic_not_customer_policy():
    overlay = organization_overlay()
    assert overlay.organization_id == ORG
    assert overlay.layer.value == "organization"
    assert not drilling_contractor_performance_pack().response_bindings
    assert all(
        node.formula_ref is None and node.target is None
        for node in drilling_contractor_performance_pack().nodes
    )


def test_activation_is_deterministic_for_identical_synthetic_evidence():
    left = run_activation()
    right = run_activation()
    assert left.assessment == right.assessment
    assert left.business_logic_executions == right.business_logic_executions

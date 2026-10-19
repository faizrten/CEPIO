from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from cepio.bootstrap import build_runtime
from cepio.industry_iq import install_industry_iq_packs
from cepio.model import ActionRequest, Decision, ObjectRef, OntologyObject, Relationship
from cepio.reliability_iq import (
    RELIABILITY_ASSET_INTERVENTION_IQ_PACK,
    AssetReliabilityStatus,
)
from cepio.runtime import AuthorizationError, CEPIORuntime


AT = datetime(2026, 10, 19, 4, 0, tzinfo=timezone.utc)
SCENARIO_PATH = Path("generalization/industry-iq/reliability-scenarios-v0.1.yaml")
ARCHETYPE_PATH = Path("generalization/archetypes/reliability-v0.1.yaml")


def _rel(runtime, rel_type: str, source_id: str, source_type: str, target_id: str, target_type: str):
    runtime.add_relationship(
        Relationship(
            type=rel_type,
            source=ObjectRef(id=source_id, type=source_type),
            target=ObjectRef(id=target_id, type=target_type),
        )
    )


def _runtime_with_pack():
    runtime = build_runtime()
    install_industry_iq_packs(runtime, [RELIABILITY_ASSET_INTERVENTION_IQ_PACK])
    return runtime


def _condition(
    condition_id: str,
    *,
    status: str = "HEALTHY",
    valid_to: str = "2026-10-20T04:00:00+00:00",
    signal_key: str = "bearing-vibration",
):
    return OntologyObject(
        id=condition_id,
        type="ConditionObservation",
        name=f"Condition {condition_id}",
        properties={
            "status": status,
            "signalKey": signal_key,
            "validFrom": "2026-10-19T03:00:00+00:00",
            "validTo": valid_to,
        },
    )


def _seed(*, equipment_type: str = "Equipment"):
    runtime = _runtime_with_pack()
    equipment = OntologyObject(
        id="EQ-1",
        type=equipment_type,
        name="Critical equipment 1",
        interfaces={"MaintainableAsset", "Inspectable", "RiskBearing"},
    )
    observation = _condition("COND-1")
    runtime.upsert_object(equipment)
    runtime.upsert_object(observation)
    _rel(
        runtime,
        "hasConditionObservation",
        equipment.id,
        equipment.type,
        observation.id,
        observation.type,
    )
    return runtime


def _assess(runtime, **overrides):
    payload = {
        "equipment_id": "EQ-1",
        "assessment_time": AT,
        "condition_observation_ids": ["COND-1"],
        "failure_event_ids": [],
        "work_order_ids": [],
        "risk_ids": [],
    }
    payload.update(overrides)
    return runtime.call_function("assessAssetReliability", **payload)


def _add_failure(
    runtime,
    *,
    failure_id: str = "FAIL-1",
    status: str = "ACTIVE",
    severity: str = "CRITICAL",
    equipment_id: str = "EQ-1",
):
    failure = OntologyObject(
        id=failure_id,
        type="FailureEvent",
        name=f"Failure {failure_id}",
        properties={"status": status, "severity": severity},
    )
    mode = OntologyObject(
        id=f"MODE-{failure_id}",
        type="FailureMode",
        name=f"Mode {failure_id}",
    )
    runtime.upsert_object(failure)
    runtime.upsert_object(mode)
    _rel(runtime, "failureOfEquipment", failure.id, failure.type, equipment_id, "Equipment")
    _rel(runtime, "hasFailureMode", failure.id, failure.type, mode.id, mode.type)
    return failure.id, mode.id


def _add_work_order(
    runtime,
    *,
    work_order_id: str = "WO-1",
    status: str = "OPEN",
    priority: str = "HIGH",
    equipment_id: str = "EQ-1",
):
    work_order = OntologyObject(
        id=work_order_id,
        type="WorkOrder",
        name=f"Work order {work_order_id}",
        properties={"status": status, "priority": priority},
    )
    runtime.upsert_object(work_order)
    source = runtime.get_object(equipment_id)
    _rel(runtime, "hasWorkOrder", source.id, source.type, work_order.id, work_order.type)
    return work_order.id


def _add_risk(
    runtime,
    *,
    risk_id: str = "RISK-1",
    status: str = "OPEN",
    severity: str = "HIGH",
    equipment_id: str = "EQ-1",
):
    risk = OntologyObject(
        id=risk_id,
        type="Risk",
        name=f"Risk {risk_id}",
        properties={"status": status, "severity": severity},
    )
    runtime.upsert_object(risk)
    source = runtime.get_object(equipment_id)
    _rel(runtime, "hasRisk", source.id, source.type, risk.id, risk.type)
    return risk.id


def test_reliability_archetype_is_cross_industrial_and_preserves_accountability():
    payload = yaml.safe_load(ARCHETYPE_PATH.read_text(encoding="utf-8"))
    boundary = payload["operating_boundary"]

    assert payload["domain"] == "reliability"
    assert payload["status"] == "frozen"
    assert "equipment reliability assessment and failure interpretation" in boundary["reliability_owns"]
    assert "maintenance planning, scheduling and work execution" in boundary["maintenance_owns"]
    assert "operating context and production/service consequence" in boundary["operations_owns"]
    assert payload["principles"]["cross_industrial_before_domain_specialization"] is True
    assert payload["principles"]["customer_specific_ontology_fork"] == "prohibited"
    assert payload["principles"]["customer_data_used_for_training"] is False


def test_reliability_scenario_portfolio_is_frozen_and_reuses_maintenance_deferral():
    payload = yaml.safe_load(SCENARIO_PATH.read_text(encoding="utf-8"))
    scenarios = payload["scenarios"]
    by_id = {item["id"]: item for item in scenarios}

    assert payload["version"] == "0.1"
    assert payload["frozen"] is True
    assert len(scenarios) == 12
    assert [item["id"] for item in scenarios] == [f"REL-IQ-{index:03d}" for index in range(1, 13)]
    assert by_id["REL-IQ-001"]["status"] == "executable-v0.1"
    assert by_id["REL-IQ-001"]["pack_id"] == "cepio.iq.reliability.asset-intervention"
    assert by_id["REL-IQ-007"]["reuses_skill"] == "cepio.skill.maintenance.assess-maintenance-deferral"
    assert payload["rules"]["canonical_ontology_changes_for_scenario_pass"] == "prohibited"
    assert payload["rules"]["synthetic_reliability_score_required"] is False


def test_reliability_iq_is_not_core_default_and_installs_only_the_assessment():
    runtime = build_runtime()
    assert runtime.has_function("assessAssetReliability") is False
    assert runtime.has_decision("maintenance-intervention-recommendation") is True
    assert runtime.has_action("CreateInspection") is True
    assert runtime.has_action("CreateWorkOrder") is True
    assert runtime.has_action("EscalateRisk") is True

    install_industry_iq_packs(runtime, [RELIABILITY_ASSET_INTERVENTION_IQ_PACK])
    assert runtime.has_function("assessAssetReliability") is True
    assert runtime.industry_iq_packs == {"cepio.iq.reliability.asset-intervention": "0.1.0"}


def test_pack_fails_closed_without_required_core_governance_capabilities():
    with pytest.raises(RuntimeError, match="requires governed Core actions"):
        RELIABILITY_ASSET_INTERVENTION_IQ_PACK.install(CEPIORuntime())


def test_healthy_current_condition_is_reliable_without_synthetic_score():
    result = _assess(_seed())
    assert result.status == AssetReliabilityStatus.reliable
    assert result.findings == []
    assert result.recommended_action is None
    assert result.evidence_ids == ["COND-1", "EQ-1"]
    assert "continued service" in result.recommendation


def test_drilling_equipment_subclass_uses_same_reliability_iq_semantics():
    result = _assess(_seed(equipment_type="DrillingEquipment"))
    assert result.status == AssetReliabilityStatus.reliable
    assert result.equipment_id == "EQ-1"


def test_warning_condition_is_degraded_and_recommends_inspection():
    runtime = _seed()
    observation = runtime.get_object("COND-1")
    observation.properties["status"] = "WARNING"
    runtime.upsert_object(observation, expected_version=observation.version)

    result = _assess(runtime)
    assert result.status == AssetReliabilityStatus.degraded
    assert result.findings[0].code == "condition.degraded"
    assert result.findings[0].severity == "advisory"
    assert result.recommended_action == "CreateInspection"


def test_critical_condition_requires_intervention_and_recommends_inspection():
    runtime = _seed()
    observation = runtime.get_object("COND-1")
    observation.properties["status"] = "CRITICAL"
    runtime.upsert_object(observation, expected_version=observation.version)

    result = _assess(runtime)
    assert result.status == AssetReliabilityStatus.intervention_required
    assert result.findings[0].code == "condition.material-degradation"
    assert result.recommended_action == "CreateInspection"


def test_active_critical_failure_requires_work_order_and_preserves_failure_mode_evidence():
    runtime = _seed()
    failure_id, mode_id = _add_failure(runtime)

    result = _assess(runtime, failure_event_ids=[failure_id])
    assert result.status == AssetReliabilityStatus.intervention_required
    assert result.recommended_action == "CreateWorkOrder"
    assert failure_id in result.evidence_ids
    assert mode_id in result.evidence_ids
    assert set(result.findings[0].evidence_ids) == {failure_id, mode_id}


def test_high_active_risk_has_priority_and_recommends_governed_escalation():
    runtime = _seed()
    risk_id = _add_risk(runtime)

    result = _assess(runtime, risk_ids=[risk_id])
    assert result.status == AssetReliabilityStatus.intervention_required
    assert result.recommended_action == "EscalateRisk"
    assert result.findings[0].code == "risk.active"


def test_high_priority_work_is_degraded_and_critical_work_requires_intervention():
    runtime = _seed()
    high_id = _add_work_order(runtime, priority="HIGH")
    degraded = _assess(runtime, work_order_ids=[high_id])
    assert degraded.status == AssetReliabilityStatus.degraded
    assert degraded.findings[0].code == "maintenance.high-priority-work"
    assert degraded.recommended_action is None

    runtime = _seed()
    critical_id = _add_work_order(runtime, priority="CRITICAL")
    intervention = _assess(runtime, work_order_ids=[critical_id])
    assert intervention.status == AssetReliabilityStatus.intervention_required
    assert intervention.findings[0].code == "maintenance.critical-work"
    assert intervention.recommended_action is None
    assert "human maintenance review" in intervention.recommendation


def test_blocked_or_overdue_work_is_intervention_evidence_without_invented_action_mapping():
    runtime = _seed()
    work_order_id = _add_work_order(runtime, status="OVERDUE", priority="MEDIUM")

    result = _assess(runtime, work_order_ids=[work_order_id])
    assert result.status == AssetReliabilityStatus.intervention_required
    assert result.findings[0].code == "maintenance.work-blocked"
    assert result.recommended_action is None


def test_closed_failure_risk_and_work_remain_evidence_without_triggering():
    runtime = _seed()
    failure_id, mode_id = _add_failure(runtime, status="CLOSED", severity="CRITICAL")
    risk_id = _add_risk(runtime, status="MITIGATED", severity="CRITICAL")
    work_order_id = _add_work_order(runtime, status="COMPLETED", priority="CRITICAL")

    result = _assess(
        runtime,
        failure_event_ids=[failure_id],
        risk_ids=[risk_id],
        work_order_ids=[work_order_id],
    )
    assert result.status == AssetReliabilityStatus.reliable
    assert result.findings == []
    assert {failure_id, mode_id, risk_id, work_order_id}.issubset(result.evidence_ids)


def test_current_condition_evidence_must_be_temporally_valid():
    runtime = _seed()
    observation = runtime.get_object("COND-1")
    observation.properties["validTo"] = "2026-10-19T03:59:59+00:00"
    runtime.upsert_object(observation, expected_version=observation.version)
    with pytest.raises(ValueError, match="COND-1 is stale at assessment time"):
        _assess(runtime)

    runtime = _seed()
    observation = runtime.get_object("COND-1")
    observation.properties.pop("validTo")
    runtime.upsert_object(observation, expected_version=observation.version)
    with pytest.raises(ValueError, match="missing required validity horizon"):
        _assess(runtime)

    runtime = _seed()
    observation = runtime.get_object("COND-1")
    observation.properties["validFrom"] = "2026-10-19T04:00:01+00:00"
    runtime.upsert_object(observation, expected_version=observation.version)
    with pytest.raises(ValueError, match="not yet valid"):
        _assess(runtime)


def test_assessment_requires_timezone_context():
    with pytest.raises(ValueError, match="assessment_time must include timezone context"):
        _assess(_seed(), assessment_time=datetime(2026, 10, 19, 4, 0))


def test_condition_evidence_must_be_equipment_scoped():
    runtime = _seed()
    runtime.upsert_object(OntologyObject(id="EQ-2", type="Equipment", name="Other equipment"))
    other = _condition("COND-OTHER")
    runtime.upsert_object(other)
    _rel(runtime, "hasConditionObservation", "EQ-2", "Equipment", other.id, other.type)

    with pytest.raises(ValueError, match="not linked to equipment EQ-1"):
        _assess(runtime, condition_observation_ids=[other.id])


def test_conflicting_current_condition_evidence_fails_closed():
    runtime = _seed()
    second = _condition("COND-2", status="CRITICAL", signal_key="bearing-vibration")
    runtime.upsert_object(second)
    _rel(runtime, "hasConditionObservation", "EQ-1", "Equipment", second.id, second.type)

    with pytest.raises(ValueError, match="Conflicting current condition evidence"):
        _assess(runtime, condition_observation_ids=["COND-1", "COND-2"])


def test_active_failure_requires_scope_failure_mode_and_supported_status_severity():
    runtime = _seed()
    failure_id, _ = _add_failure(runtime, equipment_id="EQ-1")
    failure = runtime.get_object(failure_id)
    for mode in runtime.neighbors(failure_id, "hasFailureMode"):
        # There is no delete relationship primitive; seed a fresh unmodeled active failure instead.
        assert mode.type == "FailureMode"

    unmodeled = OntologyObject(
        id="FAIL-NOMODE",
        type="FailureEvent",
        name="Unmodeled failure",
        properties={"status": "ACTIVE", "severity": "HIGH"},
    )
    runtime.upsert_object(unmodeled)
    _rel(runtime, "failureOfEquipment", unmodeled.id, unmodeled.type, "EQ-1", "Equipment")
    with pytest.raises(ValueError, match="has no FailureMode evidence"):
        _assess(runtime, failure_event_ids=[unmodeled.id])

    runtime = _seed()
    failure_id, _ = _add_failure(runtime, status="PENDING")
    with pytest.raises(ValueError, match="unsupported status PENDING"):
        _assess(runtime, failure_event_ids=[failure_id])

    runtime = _seed()
    failure_id, _ = _add_failure(runtime, severity="UNKNOWN")
    with pytest.raises(ValueError, match="Unsupported normalized severity UNKNOWN"):
        _assess(runtime, failure_event_ids=[failure_id])


def test_work_order_and_risk_evidence_must_be_scoped_and_normalized():
    runtime = _seed()
    runtime.upsert_object(
        OntologyObject(
            id="WO-UNSCOPED",
            type="WorkOrder",
            name="Unscoped work",
            properties={"status": "OPEN", "priority": "HIGH"},
        )
    )
    with pytest.raises(ValueError, match="not linked to equipment EQ-1"):
        _assess(runtime, work_order_ids=["WO-UNSCOPED"])

    runtime = _seed()
    work_order_id = _add_work_order(runtime, status="UNKNOWN", priority="HIGH")
    with pytest.raises(ValueError, match="unsupported status UNKNOWN"):
        _assess(runtime, work_order_ids=[work_order_id])

    runtime = _seed()
    work_order_id = _add_work_order(runtime, status="OPEN", priority="UNKNOWN")
    with pytest.raises(ValueError, match="unsupported priority UNKNOWN"):
        _assess(runtime, work_order_ids=[work_order_id])

    runtime = _seed()
    runtime.upsert_object(
        OntologyObject(
            id="RISK-UNSCOPED",
            type="Risk",
            name="Unscoped risk",
            properties={"status": "OPEN", "severity": "HIGH"},
        )
    )
    with pytest.raises(ValueError, match="not linked to equipment EQ-1"):
        _assess(runtime, risk_ids=["RISK-UNSCOPED"])


def test_reliability_recommendation_preserves_decision_to_human_action_boundary():
    runtime = _seed()
    risk_id = _add_risk(runtime, severity="CRITICAL")
    assessment = _assess(runtime, risk_ids=[risk_id])
    assert assessment.recommended_action == "EscalateRisk"

    decision = runtime.save_decision(
        Decision(
            decision_type="maintenance-intervention-recommendation",
            subject=ObjectRef(id="EQ-1", type="Equipment"),
            problem="Does current reliability evidence require intervention?",
            observations=[item.message for item in assessment.findings],
            recommendation=assessment.recommendation,
            recommended_action=assessment.recommended_action,
            created_by="reliability-iq-agent-1",
        )
    )
    request = ActionRequest(
        action_type="EscalateRisk",
        target=ObjectRef(id="EQ-1", type="Equipment"),
        actor_id="reliability-iq-agent-1",
        actor_roles={"ai_agent_recommender"},
        parameters={"risk_status": "escalated"},
        decision_id=decision.id,
    )
    with pytest.raises(AuthorizationError):
        runtime.execute_action(request)

    executed = runtime.execute_action(
        request.model_copy(
            update={
                "actor_id": "reliability-engineer-1",
                "actor_roles": {"reliability_engineer"},
            }
        )
    )
    assert executed.status.value == "executed"
    assert executed.effects["risk_status"] == "escalated"
    assert runtime.get_object("EQ-1").properties["riskStatus"] == "escalated"
    assert runtime.all_audits()[-1].decision_id == decision.id


def test_existing_maintenance_deferral_capability_remains_separate_and_available():
    runtime = _runtime_with_pack()
    assert runtime.has_function("evaluateMaintenanceDeferralRisk") is True
    assert runtime.has_decision("maintenance-deferral-decision") is True
    assert runtime.has_action("DeferWorkOrder") is True

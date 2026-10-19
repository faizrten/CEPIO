from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cepio.bootstrap import build_runtime
from cepio.industry_iq import install_industry_iq_packs
from cepio.model import ActionRequest, ObjectRef, OntologyObject, Relationship
from cepio.reliability_iq import (
    RELIABILITY_ASSET_INTERVENTION_IQ_PACK,
    AssetReliabilityStatus,
    _aware_datetime,
    _condition_band,
    _is_a,
    _normalized_property,
    _require_type,
    _severity_band,
)
from cepio.runtime import CEPIORuntime


AT = datetime(2026, 10, 19, 4, 0, tzinfo=timezone.utc)


def _noop_action(
    request: ActionRequest,
    target: OntologyObject,
    runtime: CEPIORuntime,
) -> dict[str, object]:
    return {}


def _rel(
    runtime: CEPIORuntime,
    rel_type: str,
    source_id: str,
    source_type: str,
    target_id: str,
    target_type: str,
) -> None:
    runtime.add_relationship(
        Relationship(
            type=rel_type,
            source=ObjectRef(id=source_id, type=source_type),
            target=ObjectRef(id=target_id, type=target_type),
        )
    )


def _seed() -> CEPIORuntime:
    runtime = build_runtime()
    install_industry_iq_packs(runtime, [RELIABILITY_ASSET_INTERVENTION_IQ_PACK])
    runtime.upsert_object(OntologyObject(id="EQ-COV", type="Equipment", name="Coverage equipment"))
    runtime.upsert_object(
        OntologyObject(
            id="COND-COV",
            type="ConditionObservation",
            name="Healthy condition",
            properties={
                "status": "HEALTHY",
                "validFrom": "2026-10-19T03:00:00+00:00",
                "validTo": "2026-10-20T04:00:00+00:00",
            },
        )
    )
    _rel(
        runtime,
        "hasConditionObservation",
        "EQ-COV",
        "Equipment",
        "COND-COV",
        "ConditionObservation",
    )
    return runtime


def _assess(runtime: CEPIORuntime, **overrides: object):
    payload: dict[str, object] = {
        "equipment_id": "EQ-COV",
        "assessment_time": AT,
        "condition_observation_ids": ["COND-COV"],
        "failure_event_ids": [],
        "work_order_ids": [],
        "risk_ids": [],
    }
    payload.update(overrides)
    return runtime.call_function("assessAssetReliability", **payload)


def test_low_level_validation_helpers_cover_fail_closed_branches():
    runtime = CEPIORuntime()
    assert _is_a(runtime, "Equipment", "Equipment") is True

    runtime.upsert_object(OntologyObject(id="NOT-EQUIPMENT", type="WorkItem", name="Wrong type"))
    with pytest.raises(ValueError, match="NOT-EQUIPMENT is not a Equipment"):
        _require_type(runtime, "NOT-EQUIPMENT", "Equipment")

    with pytest.raises(ValueError, match="missing required normalized status"):
        _normalized_property(
            OntologyObject(id="NO-STATUS", type="WorkItem", name="No status"), "status"
        )

    aware = datetime(2026, 10, 19, 4, 0, tzinfo=timezone.utc)
    assert _aware_datetime(aware, label="aware") == aware
    with pytest.raises(ValueError, match="must be an ISO-8601 timestamp"):
        _aware_datetime("not-a-time", label="invalid")
    with pytest.raises(ValueError, match="must be an ISO-8601 timestamp"):
        _aware_datetime(123, label="wrong-type")
    with pytest.raises(ValueError, match="must include timezone context"):
        _aware_datetime("2026-10-19T04:00:00", label="naive")

    with pytest.raises(ValueError, match="Unsupported normalized condition status UNKNOWN"):
        _condition_band("UNKNOWN")
    assert _severity_band("MEDIUM") == "advisory"


def test_failure_must_be_scoped_to_assessed_equipment():
    runtime = _seed()
    runtime.upsert_object(OntologyObject(id="EQ-OTHER", type="Equipment", name="Other equipment"))
    runtime.upsert_object(
        OntologyObject(
            id="FAIL-OTHER",
            type="FailureEvent",
            name="Other equipment failure",
            properties={"status": "ACTIVE", "severity": "HIGH"},
        )
    )
    runtime.upsert_object(OntologyObject(id="MODE-OTHER", type="FailureMode", name="Failure mode"))
    _rel(
        runtime,
        "failureOfEquipment",
        "FAIL-OTHER",
        "FailureEvent",
        "EQ-OTHER",
        "Equipment",
    )
    _rel(
        runtime,
        "hasFailureMode",
        "FAIL-OTHER",
        "FailureEvent",
        "MODE-OTHER",
        "FailureMode",
    )

    with pytest.raises(ValueError, match="not scoped to equipment EQ-COV"):
        _assess(runtime, failure_event_ids=["FAIL-OTHER"])


def test_normal_active_work_order_is_context_without_degradation():
    runtime = _seed()
    runtime.upsert_object(
        OntologyObject(
            id="WO-NORMAL",
            type="WorkOrder",
            name="Normal planned work",
            properties={"status": "OPEN", "priority": "NORMAL"},
        )
    )
    _rel(runtime, "hasWorkOrder", "EQ-COV", "Equipment", "WO-NORMAL", "WorkOrder")

    result = _assess(runtime, work_order_ids=["WO-NORMAL"])
    assert result.status == AssetReliabilityStatus.reliable
    assert result.recommended_action is None
    assert "WO-NORMAL" in result.evidence_ids


def test_advisory_risk_maps_to_escalation_and_unknown_risk_status_fails_closed():
    runtime = _seed()
    runtime.upsert_object(
        OntologyObject(
            id="RISK-MEDIUM",
            type="Risk",
            name="Medium reliability risk",
            properties={"status": "OPEN", "severity": "MEDIUM"},
        )
    )
    _rel(runtime, "hasRisk", "EQ-COV", "Equipment", "RISK-MEDIUM", "Risk")

    result = _assess(runtime, risk_ids=["RISK-MEDIUM"])
    assert result.status == AssetReliabilityStatus.degraded
    assert result.recommended_action == "EscalateRisk"

    runtime = _seed()
    runtime.upsert_object(
        OntologyObject(
            id="RISK-PENDING",
            type="Risk",
            name="Pending reliability risk",
            properties={"status": "PENDING", "severity": "MEDIUM"},
        )
    )
    _rel(runtime, "hasRisk", "EQ-COV", "Equipment", "RISK-PENDING", "Risk")
    with pytest.raises(ValueError, match="unsupported status PENDING"):
        _assess(runtime, risk_ids=["RISK-PENDING"])


def test_pack_fails_closed_when_actions_exist_but_core_decision_is_missing():
    runtime = CEPIORuntime()
    for action_name in ("CreateInspection", "CreateWorkOrder", "EscalateRisk"):
        runtime.register_action(action_name, _noop_action, set())

    with pytest.raises(RuntimeError, match="requires Core decision maintenance-intervention-recommendation"):
        RELIABILITY_ASSET_INTERVENTION_IQ_PACK.install(runtime)

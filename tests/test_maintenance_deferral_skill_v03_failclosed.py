from __future__ import annotations

import pytest

from cepio.bootstrap import build_runtime
from cepio.model import ObjectRef, OntologyObject, Relationship


def _seed_base_case():
    runtime = build_runtime()
    runtime.upsert_object(OntologyObject(id="P-201", type="Pump", name="P-201"))
    runtime.upsert_object(
        OntologyObject(
            id="WO-201",
            type="WorkOrder",
            name="Seal replacement",
            properties={"status": "planned"},
        )
    )
    runtime.add_relationship(
        Relationship(
            type="hasWorkOrder",
            source=ObjectRef(id="P-201", type="Pump"),
            target=ObjectRef(id="WO-201", type="WorkOrder"),
        )
    )
    return runtime


def _add_risk(runtime, risk_id: str, properties: dict):
    runtime.upsert_object(
        OntologyObject(id=risk_id, type="Risk", name=risk_id, properties=properties)
    )
    runtime.add_relationship(
        Relationship(
            type="hasRisk",
            source=ObjectRef(id="P-201", type="Pump"),
            target=ObjectRef(id=risk_id, type="Risk"),
        )
    )


def test_deferral_risk_rejects_work_order_not_linked_to_equipment():
    runtime = _seed_base_case()
    runtime.upsert_object(
        OntologyObject(id="WO-OTHER", type="WorkOrder", name="Unrelated work order")
    )
    _add_risk(
        runtime,
        "RISK-201",
        {
            "currentRiskScore": 0.2,
            "deferralRiskScore": 0.3,
            "maxSupportedDeferralHours": 48.0,
        },
    )

    with pytest.raises(ValueError, match="WorkOrder WO-OTHER is not linked"):
        runtime.call_function(
            "evaluateMaintenanceDeferralRisk",
            equipment_id="P-201",
            work_order_id="WO-OTHER",
            risk_id="RISK-201",
            proposed_deferral_hours=24,
        )


def test_deferral_risk_rejects_missing_governed_property():
    runtime = _seed_base_case()
    _add_risk(
        runtime,
        "RISK-MISSING",
        {
            "currentRiskScore": 0.2,
            "maxSupportedDeferralHours": 48.0,
        },
    )

    with pytest.raises(ValueError, match="missing required governed property deferralRiskScore"):
        runtime.call_function(
            "evaluateMaintenanceDeferralRisk",
            equipment_id="P-201",
            work_order_id="WO-201",
            risk_id="RISK-MISSING",
            proposed_deferral_hours=24,
        )


def test_deferral_risk_rejects_out_of_range_governed_score():
    runtime = _seed_base_case()
    _add_risk(
        runtime,
        "RISK-RANGE",
        {
            "currentRiskScore": 1.2,
            "deferralRiskScore": 0.4,
            "maxSupportedDeferralHours": 48.0,
        },
    )

    with pytest.raises(ValueError, match="currentRiskScore must be between 0 and 1"):
        runtime.call_function(
            "evaluateMaintenanceDeferralRisk",
            equipment_id="P-201",
            work_order_id="WO-201",
            risk_id="RISK-RANGE",
            proposed_deferral_hours=24,
        )

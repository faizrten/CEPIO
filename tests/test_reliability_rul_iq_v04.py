from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from cepio.bootstrap import build_runtime
from cepio.industry_iq import install_industry_iq_packs
from cepio.model import ObjectRef, OntologyObject, Relationship
from cepio.reliability_rul_iq import (
    RELIABILITY_RUL_MAINTENANCE_WINDOW_IQ_PACK,
    LifeEstimateState,
    MaintenanceWindowCompatibility,
    RULReviewDisposition,
)
from cepio.runtime import CEPIORuntime


AT = datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc)
V03_PATH = Path("generalization/industry-iq/reliability-scenarios-v0.3.yaml")
V04_PATH = Path("generalization/industry-iq/reliability-scenarios-v0.4.yaml")


def _runtime(*, equipment_type: str = "Equipment", bare: bool = False):
    runtime = CEPIORuntime() if bare else build_runtime()
    install_industry_iq_packs(runtime, [RELIABILITY_RUL_MAINTENANCE_WINDOW_IQ_PACK])
    runtime.upsert_object(OntologyObject(id="EQ-1", type=equipment_type, name="Equipment 1"))
    return runtime


def _estimate(
    runtime,
    *,
    estimate_id: str = "RUL-1",
    equipment_id: str = "EQ-1",
    central: object = 180.0,
    confidence: object = 0.8,
    unit: object = "h",
    valid_from: object = "2026-10-19T06:00:00+00:00",
    valid_to: object = "2026-10-21T08:00:00+00:00",
    estimate_type: str = "RemainingUsefulLifeEstimate",
    link: bool = True,
):
    estimate = OntologyObject(
        id=estimate_id,
        type=estimate_type,
        name=estimate_id,
        properties={
            "remainingUsefulLife": central,
            "confidence": confidence,
            "unitSymbol": unit,
            "validFrom": valid_from,
            "validTo": valid_to,
        },
    )
    runtime.upsert_object(estimate)
    if link:
        runtime.add_relationship(
            Relationship(
                type="estimatesLifeOf",
                source=ObjectRef(id=estimate.id, type=estimate.type),
                target=ObjectRef(
                    id=equipment_id,
                    type=runtime.get_object(equipment_id).type,
                ),
            )
        )
    return estimate.id


def _work_order(
    runtime,
    work_order_id: str,
    *,
    start_hours: float = 24.0,
    end_hours: float = 72.0,
    equipment_id: str = "EQ-1",
    work_type: str = "WorkOrder",
    start: object | None = None,
    end: object | None = None,
    link: bool = True,
):
    scheduled_start = start if start is not None else AT + timedelta(hours=start_hours)
    scheduled_end = end if end is not None else AT + timedelta(hours=end_hours)
    work = OntologyObject(
        id=work_order_id,
        type=work_type,
        name=work_order_id,
        properties={"scheduledStart": scheduled_start, "scheduledEnd": scheduled_end},
    )
    runtime.upsert_object(work)
    if link:
        runtime.add_relationship(
            Relationship(
                type="hasWorkOrder",
                source=ObjectRef(
                    id=equipment_id,
                    type=runtime.get_object(equipment_id).type,
                ),
                target=ObjectRef(id=work.id, type=work.type),
            )
        )
    return work.id


def _assess(runtime, **overrides):
    payload = {
        "equipment_id": "EQ-1",
        "assessment_time": AT,
        "estimate_id": "RUL-1",
        "expected_unit_symbol": "h",
        "lower_remaining_life_hours": 120.0,
        "upper_remaining_life_hours": 240.0,
        "work_order_ids": [],
        "estimate_expiry_warning_hours": 24.0,
        "minimum_completion_margin_hours": 24.0,
        "maintenance_planning_horizon_hours": 168.0,
    }
    payload.update(overrides)
    return runtime.call_function("assessRULMaintenanceWindow", **payload)


def test_v04_portfolio_promotes_rel_iq_004_without_mutating_v03():
    v03 = yaml.safe_load(V03_PATH.read_text(encoding="utf-8"))
    v04 = yaml.safe_load(V04_PATH.read_text(encoding="utf-8"))
    old = {item["id"]: item for item in v03["scenarios"]}
    new = {item["id"]: item for item in v04["scenarios"]}

    assert v03["version"] == "0.3"
    assert old["REL-IQ-004"]["status"] == "planned"
    assert v04["version"] == "0.4"
    assert v04["frozen"] is True
    for scenario_id in ("REL-IQ-001", "REL-IQ-002", "REL-IQ-003"):
        assert new[scenario_id] == old[scenario_id]
    assert new["REL-IQ-004"]["status"] == "executable-v0.4"
    assert new["REL-IQ-004"]["pack_id"] == "cepio.iq.reliability.rul-maintenance-window"
    assert v04["rules"]["confidence_is_uncertainty_interval"] is False
    assert v04["rules"]["maintenance_window_disposition_is_direct_action"] is False


def test_pack_is_not_core_default_and_installs_as_industry_iq():
    runtime = build_runtime()
    assert runtime.has_function("assessRULMaintenanceWindow") is False
    install_industry_iq_packs(runtime, [RELIABILITY_RUL_MAINTENANCE_WINDOW_IQ_PACK])
    assert runtime.has_function("assessRULMaintenanceWindow") is True
    assert runtime.industry_iq_packs == {
        "cepio.iq.reliability.rul-maintenance-window": "0.4.0"
    }


def test_safe_window_uses_conservative_horizon_and_preserves_confidence_separately():
    runtime = _runtime()
    _estimate(runtime)
    _work_order(runtime, "WO-SAFE", start_hours=24, end_hours=72)

    result = _assess(runtime, work_order_ids=["WO-SAFE"])
    assert result.estimate_state == LifeEstimateState.current
    assert result.compatibility == MaintenanceWindowCompatibility.safe
    assert result.disposition == RULReviewDisposition.plan_maintenance_review
    assert result.selected_work_order_id == "WO-SAFE"
    assert result.lower_remaining_life_hours == 120.0
    assert result.central_remaining_life_hours == 180.0
    assert result.upper_remaining_life_hours == 240.0
    assert result.confidence == 0.8
    assert result.conservative_horizon_at == AT + timedelta(hours=120)
    assert result.central_horizon_at == AT + timedelta(hours=180)
    assert result.optimistic_horizon_at == AT + timedelta(hours=240)
    assert result.windows[0].conservative_margin_hours == 48.0
    assert result.evidence_ids == ["EQ-1", "RUL-1", "WO-SAFE"]
    assert "governed human maintenance review" in result.recommendation


def test_low_margin_window_accelerates_review():
    runtime = _runtime()
    _estimate(runtime)
    _work_order(runtime, "WO-LOW", start_hours=72, end_hours=110)

    result = _assess(runtime, work_order_ids=["WO-LOW"])
    assert result.compatibility == MaintenanceWindowCompatibility.margin_low
    assert result.disposition == RULReviewDisposition.accelerate_maintenance_review
    assert result.windows[0].conservative_margin_hours == 10.0
    assert "accelerate human planning review" in result.recommendation


def test_window_after_conservative_horizon_routes_to_risk_review():
    runtime = _runtime()
    _estimate(runtime)
    _work_order(runtime, "WO-LATE", start_hours=100, end_hours=130)

    result = _assess(runtime, work_order_ids=["WO-LATE"])
    assert result.compatibility == MaintenanceWindowCompatibility.after_conservative_horizon
    assert result.disposition == RULReviewDisposition.risk_review
    assert result.windows[0].conservative_margin_hours == -10.0
    assert "reliability risk review" in result.recommendation


def test_no_window_inside_planning_horizon_accelerates_but_long_horizon_monitors():
    runtime = _runtime()
    _estimate(runtime)
    near = _assess(runtime)
    assert near.compatibility == MaintenanceWindowCompatibility.no_qualified_window
    assert near.disposition == RULReviewDisposition.accelerate_maintenance_review
    assert near.selected_work_order_id is None

    far = _assess(runtime, lower_remaining_life_hours=200.0)
    assert far.compatibility == MaintenanceWindowCompatibility.no_qualified_window
    assert far.disposition == RULReviewDisposition.monitor
    assert "continue governed monitoring" in far.recommendation


def test_expiring_estimate_is_explicit_and_requests_refresh():
    runtime = _runtime()
    _estimate(runtime, valid_to=AT + timedelta(hours=12))

    result = _assess(runtime, lower_remaining_life_hours=200.0)
    assert result.estimate_state == LifeEstimateState.expiring_soon
    assert result.estimate_valid_to == AT + timedelta(hours=12)
    assert "Refresh the RUL estimate" in result.recommendation


def test_best_qualified_window_is_selected_even_when_a_later_window_is_unsafe():
    runtime = _runtime()
    _estimate(runtime)
    _work_order(runtime, "WO-LATE", start_hours=100, end_hours=140)
    _work_order(runtime, "WO-SAFE", start_hours=20, end_hours=60)
    _work_order(runtime, "WO-LOW", start_hours=80, end_hours=105)

    result = _assess(runtime, work_order_ids=["WO-LATE", "WO-SAFE", "WO-LOW"])
    assert result.compatibility == MaintenanceWindowCompatibility.safe
    assert result.selected_work_order_id == "WO-SAFE"
    assert [window.work_order_id for window in result.windows] == [
        "WO-SAFE",
        "WO-LOW",
        "WO-LATE",
    ]


def test_exact_minimum_margin_is_safe():
    runtime = _runtime()
    _estimate(runtime)
    _work_order(runtime, "WO-EDGE", start_hours=80, end_hours=96)

    result = _assess(runtime, work_order_ids=["WO-EDGE"])
    assert result.windows[0].conservative_margin_hours == 24.0
    assert result.compatibility == MaintenanceWindowCompatibility.safe


def test_drilling_equipment_and_bare_runtime_use_same_contract():
    runtime = _runtime(equipment_type="DrillingEquipment")
    _estimate(runtime)
    result = _assess(runtime, lower_remaining_life_hours=200.0)
    assert result.equipment_id == "EQ-1"
    assert result.disposition == RULReviewDisposition.monitor

    runtime = _runtime(bare=True)
    _estimate(runtime)
    result = _assess(runtime, lower_remaining_life_hours=200.0)
    assert result.central_remaining_life_hours == 180.0


def test_assessment_time_and_equipment_type_fail_closed():
    runtime = _runtime()
    _estimate(runtime)
    with pytest.raises(ValueError, match="assessment_time must include timezone context"):
        _assess(runtime, assessment_time=datetime(2026, 10, 19, 8, 0))

    runtime = _runtime(equipment_type="WorkOrder", bare=True)
    runtime.upsert_object(
        OntologyObject(id="RUL-1", type="RemainingUsefulLifeEstimate", name="RUL-1")
    )
    with pytest.raises(ValueError, match="EQ-1 is not a Equipment"):
        _assess(runtime)


def test_wrong_unlinked_or_ambiguous_estimate_scope_fails_closed():
    runtime = _runtime()
    _estimate(runtime, estimate_type="WorkOrder")
    with pytest.raises(ValueError, match="RUL-1 is not a RemainingUsefulLifeEstimate"):
        _assess(runtime)

    runtime = _runtime()
    _estimate(runtime, link=False)
    with pytest.raises(ValueError, match="must resolve to exactly equipment EQ-1"):
        _assess(runtime)

    runtime = _runtime()
    runtime.upsert_object(OntologyObject(id="EQ-2", type="Equipment", name="Equipment 2"))
    _estimate(runtime)
    estimate = runtime.get_object("RUL-1")
    runtime.add_relationship(
        Relationship(
            type="estimatesLifeOf",
            source=ObjectRef(id=estimate.id, type=estimate.type),
            target=ObjectRef(id="EQ-2", type="Equipment"),
        )
    )
    with pytest.raises(ValueError, match="must resolve to exactly equipment EQ-1"):
        _assess(runtime)


def test_unit_contract_fails_closed_for_missing_mismatch_or_empty_expected_unit():
    runtime = _runtime()
    _estimate(runtime, unit=None)
    with pytest.raises(ValueError, match="missing required unitSymbol"):
        _assess(runtime)

    runtime = _runtime()
    _estimate(runtime, unit="days")
    with pytest.raises(ValueError, match="does not match governed unit h"):
        _assess(runtime)

    runtime = _runtime()
    _estimate(runtime, unit="h")
    with pytest.raises(ValueError, match="expected_unit_symbol must be non-empty"):
        _assess(runtime, expected_unit_symbol=" ")


def test_central_rul_and_confidence_must_be_numeric_and_valid():
    runtime = _runtime()
    _estimate(runtime, central=None)
    with pytest.raises(ValueError, match="missing required numeric remainingUsefulLife"):
        _assess(runtime)

    runtime = _runtime()
    _estimate(runtime, central=True)
    with pytest.raises(ValueError, match="missing required numeric remainingUsefulLife"):
        _assess(runtime)

    runtime = _runtime()
    _estimate(runtime, central=0.0)
    with pytest.raises(ValueError, match="remainingUsefulLife must be positive"):
        _assess(runtime)

    runtime = _runtime()
    _estimate(runtime, confidence=None)
    with pytest.raises(ValueError, match="missing required numeric confidence"):
        _assess(runtime)

    runtime = _runtime()
    _estimate(runtime, confidence=1.1)
    with pytest.raises(ValueError, match="confidence must be between 0 and 1"):
        _assess(runtime)


def test_uncertainty_interval_must_contain_central_estimate():
    runtime = _runtime()
    _estimate(runtime, central=180.0)
    with pytest.raises(ValueError, match="lower <= central <= upper"):
        _assess(runtime, lower_remaining_life_hours=190.0)
    with pytest.raises(ValueError, match="lower <= central <= upper"):
        _assess(runtime, upper_remaining_life_hours=170.0)

    with pytest.raises(ValidationError):
        _assess(runtime, lower_remaining_life_hours=0.0)
    with pytest.raises(ValidationError):
        _assess(runtime, upper_remaining_life_hours=-1.0)


def test_estimate_validity_fails_closed_for_missing_malformed_naive_future_stale_or_reversed():
    runtime = _runtime()
    _estimate(runtime, valid_from=None)
    with pytest.raises(ValueError, match="validFrom must be an ISO-8601 timestamp"):
        _assess(runtime)

    runtime = _runtime()
    _estimate(runtime, valid_from="not-a-time")
    with pytest.raises(ValueError, match="validFrom must be an ISO-8601 timestamp"):
        _assess(runtime)

    runtime = _runtime()
    _estimate(runtime, valid_from="2026-10-19T06:00:00")
    with pytest.raises(ValueError, match="validFrom must include timezone context"):
        _assess(runtime)

    runtime = _runtime()
    _estimate(
        runtime,
        valid_from="2026-10-20T08:00:00+00:00",
        valid_to="2026-10-21T08:00:00+00:00",
    )
    with pytest.raises(ValueError, match="not yet valid"):
        _assess(runtime)

    runtime = _runtime()
    _estimate(runtime, valid_to="2026-10-19T07:59:59+00:00")
    with pytest.raises(ValueError, match="stale at assessment time"):
        _assess(runtime)

    runtime = _runtime()
    _estimate(
        runtime,
        valid_from="2026-10-19T07:00:00+00:00",
        valid_to="2026-10-19T06:00:00+00:00",
    )
    with pytest.raises(ValueError, match="invalid validity interval"):
        _assess(runtime)


def test_duplicate_wrong_type_and_unlinked_work_orders_fail_closed():
    runtime = _runtime()
    _estimate(runtime)
    _work_order(runtime, "WO-1")
    with pytest.raises(ValueError, match="Duplicate WorkOrder evidence"):
        _assess(runtime, work_order_ids=["WO-1", "WO-1"])

    runtime = _runtime()
    _estimate(runtime)
    _work_order(runtime, "WO-WRONG", work_type="ConditionObservation")
    with pytest.raises(ValueError, match="WO-WRONG is not a WorkOrder"):
        _assess(runtime, work_order_ids=["WO-WRONG"])

    runtime = _runtime()
    _estimate(runtime)
    _work_order(runtime, "WO-UNLINKED", link=False)
    with pytest.raises(ValueError, match="not linked to equipment EQ-1"):
        _assess(runtime, work_order_ids=["WO-UNLINKED"])


def test_work_order_schedule_must_be_complete_aware_future_and_positive_duration():
    runtime = _runtime()
    _estimate(runtime)
    _work_order(runtime, "WO-MISSING", start=None, end=AT + timedelta(hours=40))
    runtime.get_object("WO-MISSING").properties["scheduledStart"] = None
    with pytest.raises(ValueError, match="scheduledStart must be an ISO-8601 timestamp"):
        _assess(runtime, work_order_ids=["WO-MISSING"])

    runtime = _runtime()
    _estimate(runtime)
    _work_order(
        runtime,
        "WO-NAIVE",
        start=datetime(2026, 10, 20, 8, 0),
        end=datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(ValueError, match="scheduledStart must include timezone context"):
        _assess(runtime, work_order_ids=["WO-NAIVE"])

    runtime = _runtime()
    _estimate(runtime)
    _work_order(
        runtime,
        "WO-REVERSED",
        start=AT + timedelta(hours=20),
        end=AT + timedelta(hours=10),
    )
    with pytest.raises(ValueError, match="invalid scheduled window"):
        _assess(runtime, work_order_ids=["WO-REVERSED"])

    runtime = _runtime()
    _estimate(runtime)
    _work_order(
        runtime,
        "WO-STARTED",
        start=AT - timedelta(hours=1),
        end=AT + timedelta(hours=10),
    )
    with pytest.raises(ValueError, match="has already started"):
        _assess(runtime, work_order_ids=["WO-STARTED"])


def test_duplicate_schedule_intervals_fail_closed():
    runtime = _runtime()
    _estimate(runtime)
    _work_order(runtime, "WO-1", start_hours=24, end_hours=48)
    _work_order(runtime, "WO-2", start_hours=24, end_hours=48)

    with pytest.raises(ValueError, match="Ambiguous duplicate WorkOrder schedule interval"):
        _assess(runtime, work_order_ids=["WO-1", "WO-2"])


def test_input_model_validates_governed_thresholds():
    runtime = _runtime()
    _estimate(runtime)
    with pytest.raises(ValidationError):
        _assess(runtime, estimate_expiry_warning_hours=-1.0)
    with pytest.raises(ValidationError):
        _assess(runtime, minimum_completion_margin_hours=-1.0)
    with pytest.raises(ValidationError):
        _assess(runtime, maintenance_planning_horizon_hours=0.0)

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from cepio.bootstrap import build_runtime
from cepio.industry_iq import install_industry_iq_packs
from cepio.model import ObjectRef, OntologyObject, Relationship
from cepio.reliability_condition_iq import (
    RELIABILITY_CONDITION_MONITORING_IQ_PACK,
    ConditionDeviationStatus,
    ConditionReviewDisposition,
    ConditionTrend,
)
from cepio.runtime import CEPIORuntime


AT = datetime(2026, 10, 19, 8, 0, tzinfo=timezone.utc)
V02_PATH = Path("generalization/industry-iq/reliability-scenarios-v0.2.yaml")
V03_PATH = Path("generalization/industry-iq/reliability-scenarios-v0.3.yaml")


def _runtime(*, equipment_type: str = "Equipment", bare: bool = False):
    runtime = CEPIORuntime() if bare else build_runtime()
    install_industry_iq_packs(runtime, [RELIABILITY_CONDITION_MONITORING_IQ_PACK])
    runtime.upsert_object(OntologyObject(id="EQ-1", type=equipment_type, name="Equipment 1"))
    return runtime


def _observation(
    runtime,
    observation_id: str,
    *,
    value: object,
    observed_at: object = "2026-10-19T07:30:00+00:00",
    unit: object = "mm/s",
    equipment_id: str = "EQ-1",
):
    observation = OntologyObject(
        id=observation_id,
        type="ConditionObservation",
        name=observation_id,
        properties={"value": value, "observedAt": observed_at, "unitSymbol": unit},
    )
    runtime.upsert_object(observation)
    runtime.add_relationship(
        Relationship(
            type="hasConditionObservation",
            source=ObjectRef(id=equipment_id, type=runtime.get_object(equipment_id).type),
            target=ObjectRef(id=observation.id, type=observation.type),
        )
    )
    return observation.id


def _signal(observation_ids, **overrides):
    payload = {
        "signal_key": "bearing-vibration",
        "observation_ids": list(observation_ids),
        "unit_symbol": "mm/s",
        "normal_low": 0.0,
        "normal_high": 4.0,
        "advisory_low": -1.0,
        "advisory_high": 6.0,
        "material_low": -2.0,
        "material_high": 8.0,
        "max_observation_age_hours": 24.0,
        "trend_epsilon": 0.05,
    }
    payload.update(overrides)
    return payload


def _assess(runtime, signals, **overrides):
    payload = {"equipment_id": "EQ-1", "assessment_time": AT, "signals": signals}
    payload.update(overrides)
    return runtime.call_function("assessConditionMonitoring", **payload)


def test_v03_portfolio_freezes_condition_monitoring_without_mutating_v02():
    v02 = yaml.safe_load(V02_PATH.read_text(encoding="utf-8"))
    v03 = yaml.safe_load(V03_PATH.read_text(encoding="utf-8"))
    old = {item["id"]: item for item in v02["scenarios"]}
    new = {item["id"]: item for item in v03["scenarios"]}

    assert v02["version"] == "0.2"
    assert old["REL-IQ-003"]["status"] == "planned"
    assert v03["version"] == "0.3"
    assert v03["frozen"] is True
    assert new["REL-IQ-001"] == old["REL-IQ-001"]
    assert new["REL-IQ-002"] == old["REL-IQ-002"]
    assert new["REL-IQ-003"]["status"] == "executable-v0.3"
    assert new["REL-IQ-003"]["pack_id"] == "cepio.iq.reliability.condition-monitoring"
    assert v03["rules"]["condition_disposition_is_direct_action"] is False
    assert v03["rules"]["synthetic_reliability_score_required"] is False


def test_pack_is_not_core_default_and_installs_as_industry_iq():
    runtime = build_runtime()
    assert runtime.has_function("assessConditionMonitoring") is False
    install_industry_iq_packs(runtime, [RELIABILITY_CONDITION_MONITORING_IQ_PACK])
    assert runtime.has_function("assessConditionMonitoring") is True
    assert runtime.industry_iq_packs == {"cepio.iq.reliability.condition-monitoring": "0.3.0"}


def test_single_normal_observation_is_monitor_with_insufficient_history():
    runtime = _runtime()
    _observation(runtime, "OBS-1", value=2.0, observed_at=AT)

    result = _assess(runtime, [_signal(["OBS-1"])])
    signal = result.signals[0]
    assert result.status == ConditionDeviationStatus.normal
    assert result.disposition == ConditionReviewDisposition.monitor
    assert signal.trend == ConditionTrend.insufficient_history
    assert signal.normalized_distance_from_normal == 0.0
    assert signal.latest_observation_id == "OBS-1"
    assert result.evidence_ids == ["EQ-1", "OBS-1"]
    assert "continued monitoring" in result.recommendation


def test_in_band_history_remains_stable_and_monitor():
    runtime = _runtime()
    _observation(runtime, "OBS-1", value=1.0, observed_at="2026-10-19T06:00:00+00:00")
    _observation(runtime, "OBS-2", value=3.5, observed_at="2026-10-19T07:30:00+00:00")

    result = _assess(runtime, [_signal(["OBS-1", "OBS-2"])])
    assert result.status == ConditionDeviationStatus.normal
    assert result.signals[0].trend == ConditionTrend.stable
    assert result.disposition == ConditionReviewDisposition.monitor


def test_advisory_deterioration_routes_to_maintenance_review():
    runtime = _runtime()
    _observation(runtime, "OBS-1", value=3.0, observed_at="2026-10-19T06:00:00+00:00")
    _observation(runtime, "OBS-2", value=5.5, observed_at="2026-10-19T07:30:00+00:00")

    result = _assess(runtime, [_signal(["OBS-1", "OBS-2"])])
    assert result.status == ConditionDeviationStatus.advisory
    assert result.signals[0].trend == ConditionTrend.deteriorating
    assert result.signals[0].normalized_distance_from_normal == 0.375
    assert result.disposition == ConditionReviewDisposition.maintenance_review
    assert "maintenance review" in result.recommendation


def test_advisory_stable_routes_to_inspection_review():
    runtime = _runtime()
    _observation(runtime, "OBS-1", value=5.2, observed_at="2026-10-19T07:00:00+00:00")
    _observation(runtime, "OBS-2", value=5.3, observed_at="2026-10-19T07:30:00+00:00")

    result = _assess(runtime, [_signal(["OBS-1", "OBS-2"], trend_epsilon=0.1)])
    assert result.status == ConditionDeviationStatus.advisory
    assert result.signals[0].trend == ConditionTrend.stable
    assert result.disposition == ConditionReviewDisposition.inspection_review
    assert "inspection review" in result.recommendation


def test_material_improving_routes_to_maintenance_review():
    runtime = _runtime()
    _observation(runtime, "OBS-1", value=7.8, observed_at="2026-10-19T07:00:00+00:00")
    _observation(runtime, "OBS-2", value=6.5, observed_at="2026-10-19T07:30:00+00:00")

    result = _assess(runtime, [_signal(["OBS-1", "OBS-2"])])
    assert result.status == ConditionDeviationStatus.material
    assert result.signals[0].trend == ConditionTrend.improving
    assert result.disposition == ConditionReviewDisposition.maintenance_review


def test_material_deteriorating_escalates_to_risk_review():
    runtime = _runtime()
    _observation(runtime, "OBS-1", value=6.2, observed_at="2026-10-19T07:00:00+00:00")
    _observation(runtime, "OBS-2", value=7.8, observed_at="2026-10-19T07:30:00+00:00")

    result = _assess(runtime, [_signal(["OBS-1", "OBS-2"])])
    assert result.status == ConditionDeviationStatus.material
    assert result.signals[0].trend == ConditionTrend.deteriorating
    assert result.disposition == ConditionReviewDisposition.risk_review
    assert "risk review" in result.recommendation


def test_critical_high_and_low_values_are_risk_review():
    runtime = _runtime()
    _observation(runtime, "OBS-HIGH", value=9.0)
    high = _assess(runtime, [_signal(["OBS-HIGH"])])
    assert high.status == ConditionDeviationStatus.critical
    assert high.disposition == ConditionReviewDisposition.risk_review

    runtime = _runtime()
    _observation(runtime, "OBS-LOW", value=-3.0)
    low = _assess(runtime, [_signal(["OBS-LOW"])])
    assert low.status == ConditionDeviationStatus.critical
    assert low.signals[0].normalized_distance_from_normal == 0.75


def test_below_normal_advisory_distance_and_improving_trend_are_direction_agnostic():
    runtime = _runtime()
    _observation(runtime, "OBS-1", value=-1.5, observed_at="2026-10-19T07:00:00+00:00")
    _observation(runtime, "OBS-2", value=-0.5, observed_at="2026-10-19T07:30:00+00:00")

    result = _assess(runtime, [_signal(["OBS-1", "OBS-2"])])
    assert result.status == ConditionDeviationStatus.advisory
    assert result.signals[0].trend == ConditionTrend.improving
    assert result.signals[0].normalized_distance_from_normal == 0.125
    assert result.disposition == ConditionReviewDisposition.inspection_review


def test_multiple_signals_use_most_severe_status_and_disposition():
    runtime = _runtime()
    _observation(runtime, "VIB-1", value=2.0, unit="mm/s")
    _observation(runtime, "TEMP-1", value=115.0, unit="degC")

    result = _assess(
        runtime,
        [
            _signal(["VIB-1"]),
            _signal(
                ["TEMP-1"],
                signal_key="bearing-temperature",
                unit_symbol="degC",
                normal_low=20.0,
                normal_high=80.0,
                advisory_low=10.0,
                advisory_high=90.0,
                material_low=0.0,
                material_high=110.0,
            ),
        ],
    )
    assert result.status == ConditionDeviationStatus.critical
    assert result.disposition == ConditionReviewDisposition.risk_review
    assert result.evidence_ids == ["EQ-1", "TEMP-1", "VIB-1"]


def test_drilling_equipment_uses_same_condition_monitoring_semantics():
    runtime = _runtime(equipment_type="DrillingEquipment")
    _observation(runtime, "OBS-1", value=5.0)

    result = _assess(runtime, [_signal(["OBS-1"])])
    assert result.status == ConditionDeviationStatus.advisory
    assert result.equipment_id == "EQ-1"


def test_bare_runtime_without_type_registry_uses_same_generic_contract():
    runtime = _runtime(bare=True)
    _observation(runtime, "OBS-1", value=2.0)
    result = _assess(runtime, [_signal(["OBS-1"])])
    assert result.status == ConditionDeviationStatus.normal


def test_assessment_time_and_equipment_type_fail_closed():
    runtime = _runtime()
    _observation(runtime, "OBS-1", value=2.0)
    with pytest.raises(ValueError, match="assessment_time must include timezone context"):
        _assess(runtime, [_signal(["OBS-1"])], assessment_time=datetime(2026, 10, 19, 8, 0))

    runtime = _runtime(equipment_type="WorkOrder", bare=True)
    with pytest.raises(ValueError, match="EQ-1 is not a Equipment"):
        _assess(runtime, [_signal(["DOES-NOT-MATTER"])])


def test_duplicate_signal_or_observation_evidence_fails_closed():
    runtime = _runtime()
    _observation(runtime, "OBS-1", value=2.0)
    with pytest.raises(ValueError, match="Duplicate governed signal_key"):
        _assess(runtime, [_signal(["OBS-1"]), _signal(["OBS-1"])])

    _observation(runtime, "OBS-2", value=3.0, observed_at="2026-10-19T07:00:00+00:00")
    with pytest.raises(ValueError, match="Duplicate ConditionObservation evidence"):
        _assess(
            runtime,
            [
                _signal(["OBS-1", "OBS-2"]),
                _signal(["OBS-2"], signal_key="other-signal"),
            ],
        )


def test_invalid_signal_identity_unit_and_envelopes_fail_closed():
    runtime = _runtime()
    _observation(runtime, "OBS-1", value=2.0)

    with pytest.raises(ValueError, match="signal_key must be non-empty"):
        _assess(runtime, [_signal(["OBS-1"], signal_key=" ")])
    with pytest.raises(ValueError, match="unit_symbol must be non-empty"):
        _assess(runtime, [_signal(["OBS-1"], unit_symbol=" ")])
    with pytest.raises(ValueError, match="normal envelope must have positive width"):
        _assess(runtime, [_signal(["OBS-1"], normal_low=4.0, normal_high=4.0)])
    with pytest.raises(ValueError, match="envelopes must be nested"):
        _assess(runtime, [_signal(["OBS-1"], advisory_high=3.0)])


def test_wrong_observation_type_and_unlinked_evidence_fail_closed():
    runtime = _runtime()
    runtime.upsert_object(OntologyObject(id="OBS-WRONG", type="WorkOrder", name="wrong"))
    with pytest.raises(ValueError, match="OBS-WRONG is not a ConditionObservation"):
        _assess(runtime, [_signal(["OBS-WRONG"])])

    runtime = _runtime()
    runtime.upsert_object(
        OntologyObject(
            id="OBS-UNLINKED",
            type="ConditionObservation",
            name="unlinked",
            properties={"value": 2.0, "observedAt": AT, "unitSymbol": "mm/s"},
        )
    )
    with pytest.raises(ValueError, match="not linked to equipment EQ-1"):
        _assess(runtime, [_signal(["OBS-UNLINKED"])])


def test_missing_mismatched_and_trimmed_unit_behavior():
    runtime = _runtime()
    _observation(runtime, "OBS-MISSING", value=2.0, unit=None)
    with pytest.raises(ValueError, match="missing required unitSymbol"):
        _assess(runtime, [_signal(["OBS-MISSING"])])

    runtime = _runtime()
    _observation(runtime, "OBS-MISMATCH", value=2.0, unit="in/s")
    with pytest.raises(ValueError, match="does not match governed unit mm/s"):
        _assess(runtime, [_signal(["OBS-MISMATCH"])])

    runtime = _runtime()
    _observation(runtime, "OBS-TRIM", value=2.0, unit=" mm/s ")
    result = _assess(runtime, [_signal(["OBS-TRIM"], unit_symbol=" mm/s ")])
    assert result.signals[0].unit_symbol == "mm/s"


def test_observation_time_parsing_and_temporal_scope_fail_closed():
    runtime = _runtime()
    _observation(runtime, "OBS-BAD", value=2.0, observed_at="not-a-time")
    with pytest.raises(ValueError, match="must be an ISO-8601 timestamp"):
        _assess(runtime, [_signal(["OBS-BAD"])])

    runtime = _runtime()
    _observation(runtime, "OBS-TYPE", value=2.0, observed_at=123)
    with pytest.raises(ValueError, match="must be an ISO-8601 timestamp"):
        _assess(runtime, [_signal(["OBS-TYPE"])])

    runtime = _runtime()
    _observation(runtime, "OBS-NAIVE", value=2.0, observed_at=datetime(2026, 10, 19, 7, 0))
    with pytest.raises(ValueError, match="must include timezone context"):
        _assess(runtime, [_signal(["OBS-NAIVE"])])

    runtime = _runtime()
    _observation(runtime, "OBS-FUTURE", value=2.0, observed_at="2026-10-19T08:00:01+00:00")
    with pytest.raises(ValueError, match="future evidence"):
        _assess(runtime, [_signal(["OBS-FUTURE"])])

    runtime = _runtime()
    _observation(runtime, "OBS-STALE", value=2.0, observed_at="2026-10-18T07:59:00+00:00")
    with pytest.raises(ValueError, match="is stale for signal"):
        _assess(runtime, [_signal(["OBS-STALE"], max_observation_age_hours=24.0)])


def test_duplicate_observation_time_fails_closed():
    runtime = _runtime()
    _observation(runtime, "OBS-1", value=2.0, observed_at="2026-10-19T07:30:00+00:00")
    _observation(runtime, "OBS-2", value=3.0, observed_at="2026-10-19T07:30:00+00:00")
    with pytest.raises(ValueError, match="ambiguous duplicate observation time"):
        _assess(runtime, [_signal(["OBS-1", "OBS-2"])])


def test_numeric_value_is_required_and_boolean_is_not_numeric_evidence():
    runtime = _runtime()
    _observation(runtime, "OBS-NONE", value=None)
    with pytest.raises(ValueError, match="missing required numeric value"):
        _assess(runtime, [_signal(["OBS-NONE"])])

    runtime = _runtime()
    _observation(runtime, "OBS-BOOL", value=True)
    with pytest.raises(ValueError, match="missing required numeric value"):
        _assess(runtime, [_signal(["OBS-BOOL"])])


def test_pydantic_guards_empty_signals_observations_and_negative_tolerances():
    runtime = _runtime()
    with pytest.raises(ValidationError):
        _assess(runtime, [])
    with pytest.raises(ValidationError):
        _assess(runtime, [_signal([])])
    with pytest.raises(ValidationError):
        _assess(runtime, [_signal(["X"], max_observation_age_hours=0.0)])
    with pytest.raises(ValidationError):
        _assess(runtime, [_signal(["X"], trend_epsilon=-0.1)])

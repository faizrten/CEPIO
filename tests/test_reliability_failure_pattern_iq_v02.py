from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from cepio.bootstrap import build_runtime
from cepio.industry_iq import install_industry_iq_packs
from cepio.model import ObjectRef, OntologyObject, Relationship
from cepio.reliability_failure_pattern_iq import (
    RELIABILITY_FAILURE_PATTERN_IQ_PACK,
    FailurePatternStatus,
    ReliabilityStrategyResponse,
    assess_failure_pattern_recurrence,
)
from cepio.reliability_iq import RELIABILITY_ASSET_INTERVENTION_IQ_PACK
from cepio.runtime import CEPIORuntime


START = datetime(2026, 10, 1, tzinfo=timezone.utc)
END = datetime(2026, 11, 1, tzinfo=timezone.utc)
SCENARIO_V01 = Path("generalization/industry-iq/reliability-scenarios-v0.1.yaml")
SCENARIO_V02 = Path("generalization/industry-iq/reliability-scenarios-v0.2.yaml")


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


def _runtime() -> CEPIORuntime:
    runtime = build_runtime()
    install_industry_iq_packs(
        runtime,
        [RELIABILITY_ASSET_INTERVENTION_IQ_PACK, RELIABILITY_FAILURE_PATTERN_IQ_PACK],
    )
    return runtime


def _equipment(runtime: CEPIORuntime, equipment_id: str, *, equipment_type: str = "Equipment"):
    obj = OntologyObject(
        id=equipment_id,
        type=equipment_type,
        name=f"Equipment {equipment_id}",
    )
    runtime.upsert_object(obj)
    return obj


def _failure(
    runtime: CEPIORuntime,
    failure_id: str,
    equipment_id: str,
    failure_mode_id: str,
    *,
    occurred_at: object = "2026-10-10T04:00:00+00:00",
    cause: object = "bearing degradation",
) -> str:
    equipment = runtime.get_object(equipment_id)
    properties: dict[str, object] = {"startTime": occurred_at}
    if cause is not None:
        properties["cause"] = cause
    event = OntologyObject(
        id=failure_id,
        type="FailureEvent",
        name=f"Failure {failure_id}",
        properties=properties,
    )
    runtime.upsert_object(event)
    try:
        runtime.get_object(failure_mode_id)
    except KeyError:
        runtime.upsert_object(
            OntologyObject(
                id=failure_mode_id,
                type="FailureMode",
                name=f"Failure mode {failure_mode_id}",
            )
        )
    _rel(
        runtime,
        "failureOfEquipment",
        event.id,
        event.type,
        equipment.id,
        equipment.type,
    )
    _rel(
        runtime,
        "hasFailureMode",
        event.id,
        event.type,
        failure_mode_id,
        "FailureMode",
    )
    return event.id


def _assess(runtime: CEPIORuntime, failure_event_ids: list[str], **overrides):
    payload = {
        "analysis_start": START,
        "analysis_end": END,
        "failure_event_ids": failure_event_ids,
        "max_expected_events_per_equipment_mode": 2,
        "max_expected_events_per_failure_mode_population": 3,
        "min_distinct_equipment_for_systemic": 2,
        "min_common_cause_events": 2,
    }
    payload.update(overrides)
    return runtime.call_function("assessFailurePatternRecurrence", **payload)


def test_v02_promotes_rel_iq_002_without_mutating_frozen_v01_portfolio():
    v01 = yaml.safe_load(SCENARIO_V01.read_text(encoding="utf-8"))
    v02 = yaml.safe_load(SCENARIO_V02.read_text(encoding="utf-8"))
    old_by_id = {item["id"]: item for item in v01["scenarios"]}
    new_by_id = {item["id"]: item for item in v02["scenarios"]}

    assert v01["version"] == "0.1"
    assert old_by_id["REL-IQ-002"]["status"] == "planned"
    assert v02["version"] == "0.2"
    assert v02["frozen"] is True
    assert new_by_id["REL-IQ-001"]["status"] == "executable-v0.1"
    assert new_by_id["REL-IQ-002"]["status"] == "executable-v0.2"
    assert new_by_id["REL-IQ-002"]["pack_id"] == "cepio.iq.reliability.failure-pattern-recurrence"
    assert v02["rules"]["recorded_common_cause_is_proven_root_cause"] is False
    assert v02["rules"]["bad_actor_ranking_requires_exposure_normalization"] is True


def test_failure_pattern_pack_is_additive_and_not_core_default():
    runtime = build_runtime()
    assert runtime.has_function("assessFailurePatternRecurrence") is False

    install_industry_iq_packs(
        runtime,
        [RELIABILITY_ASSET_INTERVENTION_IQ_PACK, RELIABILITY_FAILURE_PATTERN_IQ_PACK],
    )

    assert runtime.has_function("assessAssetReliability") is True
    assert runtime.has_function("assessFailurePatternRecurrence") is True
    assert runtime.industry_iq_packs == {
        "cepio.iq.reliability.asset-intervention": "0.1.0",
        "cepio.iq.reliability.failure-pattern-recurrence": "0.2.0",
    }
    assert runtime.has_action("ReviewReliabilityStrategy") is False
    assert runtime.has_decision("reliability-strategy-review-recommendation") is False


def test_within_expectation_preserves_population_evidence_without_inventing_pattern():
    runtime = _runtime()
    _equipment(runtime, "EQ-1")
    _equipment(runtime, "EQ-2")
    ids = [
        _failure(runtime, "F-1", "EQ-1", "FM-BRG", cause="bearing degradation"),
        _failure(runtime, "F-2", "EQ-2", "FM-BRG", cause="lubrication loss"),
    ]

    result = _assess(runtime, ids)

    assert result.status == FailurePatternStatus.within_expectation
    assert result.strategy_response == ReliabilityStrategyResponse.monitor
    assert result.recurring_equipment_ids == []
    assert result.recurring_failure_mode_ids == []
    assert result.systemic_failure_mode_ids == []
    assert result.common_cause_evidence == []
    assert result.patterns[0].event_count == 2
    assert set(result.evidence_ids) == {"EQ-1", "EQ-2", "F-1", "F-2", "FM-BRG"}


def test_local_recurrence_surfaces_repeated_recorded_cause_without_claiming_root_cause():
    runtime = _runtime()
    _equipment(runtime, "EQ-1")
    ids = [
        _failure(runtime, "F-1", "EQ-1", "FM-BRG", cause="bearing degradation"),
        _failure(runtime, "F-2", "EQ-1", "FM-BRG", cause=" Bearing   Degradation "),
        _failure(runtime, "F-3", "EQ-1", "FM-BRG", cause="bearing degradation"),
    ]

    result = _assess(runtime, ids)

    assert result.status == FailurePatternStatus.local_recurrence
    assert result.strategy_response == ReliabilityStrategyResponse.local_engineering_review
    assert result.recurring_equipment_ids == ["EQ-1"]
    assert result.recurring_failure_mode_ids == ["FM-BRG"]
    assert result.systemic_failure_mode_ids == []
    common = result.common_cause_evidence[0]
    assert common.cause == "BEARING DEGRADATION"
    assert common.event_count == 3
    assert common.equipment_ids == ["EQ-1"]
    assert common.cross_equipment is False
    assert "bad-actor conclusion" in result.recommendation


def test_systemic_recurrence_works_across_generic_and_drilling_equipment():
    runtime = _runtime()
    _equipment(runtime, "EQ-1")
    _equipment(runtime, "EQ-2", equipment_type="DrillingEquipment")
    _equipment(runtime, "EQ-3")
    ids = [
        _failure(runtime, "F-1", "EQ-1", "FM-SEAL", cause="seal material degradation"),
        _failure(runtime, "F-2", "EQ-2", "FM-SEAL", cause="seal material degradation"),
        _failure(runtime, "F-3", "EQ-3", "FM-SEAL", cause="seal material degradation"),
        _failure(runtime, "F-4", "EQ-1", "FM-SEAL", cause="seal material degradation"),
    ]

    result = _assess(runtime, ids)

    assert result.status == FailurePatternStatus.systemic_recurrence
    assert result.strategy_response == ReliabilityStrategyResponse.systemic_reliability_review
    assert result.recurring_failure_mode_ids == ["FM-SEAL"]
    assert result.systemic_failure_mode_ids == ["FM-SEAL"]
    pattern = result.patterns[0]
    assert pattern.exceeds_population_expectation is True
    assert pattern.systemic is True
    assert pattern.equipment_ids == ["EQ-1", "EQ-2", "EQ-3"]
    assert pattern.recurring_equipment_ids == []
    common = result.common_cause_evidence[0]
    assert common.cross_equipment is True
    assert common.equipment_ids == ["EQ-1", "EQ-2", "EQ-3"]
    assert "not proven root cause" in result.recommendation


def test_population_exceedance_on_one_equipment_remains_local_not_systemic():
    runtime = _runtime()
    _equipment(runtime, "EQ-1")
    ids = [_failure(runtime, f"F-{index}", "EQ-1", "FM-X", cause=None) for index in range(1, 5)]

    result = _assess(
        runtime,
        ids,
        max_expected_events_per_equipment_mode=10,
        max_expected_events_per_failure_mode_population=3,
    )

    assert result.status == FailurePatternStatus.local_recurrence
    assert result.recurring_equipment_ids == []
    assert result.recurring_failure_mode_ids == ["FM-X"]
    assert result.systemic_failure_mode_ids == []
    assert result.patterns[0].exceeds_population_expectation is True
    assert result.patterns[0].systemic is False


def test_missing_blank_or_below_threshold_cause_does_not_manufacture_common_cause():
    runtime = _runtime()
    _equipment(runtime, "EQ-1")
    ids = [
        _failure(runtime, "F-1", "EQ-1", "FM-X", cause=None),
        _failure(runtime, "F-2", "EQ-1", "FM-X", cause="   "),
        _failure(runtime, "F-3", "EQ-1", "FM-X", cause="single observation"),
    ]

    result = _assess(runtime, ids, min_common_cause_events=2)

    assert result.status == FailurePatternStatus.local_recurrence
    assert result.common_cause_evidence == []
    assert result.patterns[0].common_cause_evidence == []


def test_common_cause_threshold_is_governed_input_not_hard_coded():
    runtime = _runtime()
    _equipment(runtime, "EQ-1")
    ids = [
        _failure(runtime, "F-1", "EQ-1", "FM-X", cause="alignment"),
        _failure(runtime, "F-2", "EQ-1", "FM-X", cause="alignment"),
        _failure(runtime, "F-3", "EQ-1", "FM-X", cause="other"),
    ]

    surfaced = _assess(runtime, ids, min_common_cause_events=2)
    suppressed = _assess(runtime, ids, min_common_cause_events=3)

    assert [item.cause for item in surfaced.common_cause_evidence] == ["ALIGNMENT"]
    assert suppressed.common_cause_evidence == []


def test_duplicate_failure_ids_cannot_manufacture_recurrence():
    runtime = _runtime()
    _equipment(runtime, "EQ-1")
    failure_id = _failure(runtime, "F-1", "EQ-1", "FM-X")

    with pytest.raises(ValueError, match="Duplicate failure_event_ids"):
        _assess(runtime, [failure_id, failure_id, failure_id])


def test_failure_event_must_have_exactly_one_equipment_scope():
    runtime = _runtime()
    _equipment(runtime, "EQ-1")
    _equipment(runtime, "EQ-2")
    failure_id = _failure(runtime, "F-1", "EQ-1", "FM-X")
    _rel(runtime, "failureOfEquipment", failure_id, "FailureEvent", "EQ-2", "Equipment")

    with pytest.raises(ValueError, match="exactly one Equipment scope"):
        _assess(runtime, [failure_id])

    runtime = _runtime()
    event = OntologyObject(
        id="F-NOSCOPE",
        type="FailureEvent",
        name="Unscoped failure",
        properties={"startTime": "2026-10-10T04:00:00+00:00"},
    )
    runtime.upsert_object(event)
    runtime.upsert_object(OntologyObject(id="FM-X", type="FailureMode", name="Mode"))
    _rel(runtime, "hasFailureMode", event.id, event.type, "FM-X", "FailureMode")
    with pytest.raises(ValueError, match="exactly one Equipment scope"):
        _assess(runtime, [event.id])


def test_failure_event_rejects_non_equipment_scope_and_non_failure_mode_target():
    runtime = CEPIORuntime()
    event = OntologyObject(
        id="F-1",
        type="FailureEvent",
        name="Failure",
        properties={"startTime": "2026-10-10T04:00:00+00:00"},
    )
    wrong_equipment = OntologyObject(id="WO-1", type="WorkOrder", name="Not equipment")
    mode = OntologyObject(id="FM-1", type="FailureMode", name="Mode")
    for obj in (event, wrong_equipment, mode):
        runtime.upsert_object(obj)
    _rel(runtime, "failureOfEquipment", "F-1", "FailureEvent", "WO-1", "WorkOrder")
    _rel(runtime, "hasFailureMode", "F-1", "FailureEvent", "FM-1", "FailureMode")

    with pytest.raises(ValueError, match="target WO-1 is not Equipment"):
        assess_failure_pattern_recurrence(
            runtime=runtime,
            analysis_start=START,
            analysis_end=END,
            failure_event_ids=["F-1"],
            max_expected_events_per_equipment_mode=1,
            max_expected_events_per_failure_mode_population=1,
            min_distinct_equipment_for_systemic=2,
            min_common_cause_events=2,
        )

    runtime = CEPIORuntime()
    event = OntologyObject(
        id="F-2",
        type="FailureEvent",
        name="Failure",
        properties={"startTime": "2026-10-10T04:00:00+00:00"},
    )
    equipment = OntologyObject(id="EQ-1", type="Equipment", name="Equipment")
    wrong_mode = OntologyObject(id="RISK-1", type="Risk", name="Not failure mode")
    for obj in (event, equipment, wrong_mode):
        runtime.upsert_object(obj)
    _rel(runtime, "failureOfEquipment", "F-2", "FailureEvent", "EQ-1", "Equipment")
    _rel(runtime, "hasFailureMode", "F-2", "FailureEvent", "RISK-1", "Risk")

    with pytest.raises(ValueError, match="target RISK-1 is not FailureMode"):
        assess_failure_pattern_recurrence(
            runtime=runtime,
            analysis_start=START,
            analysis_end=END,
            failure_event_ids=["F-2"],
            max_expected_events_per_equipment_mode=1,
            max_expected_events_per_failure_mode_population=1,
            min_distinct_equipment_for_systemic=2,
            min_common_cause_events=2,
        )


def test_failure_event_must_have_exactly_one_failure_mode():
    runtime = _runtime()
    _equipment(runtime, "EQ-1")
    failure_id = _failure(runtime, "F-1", "EQ-1", "FM-1")
    runtime.upsert_object(OntologyObject(id="FM-2", type="FailureMode", name="Mode 2"))
    _rel(runtime, "hasFailureMode", failure_id, "FailureEvent", "FM-2", "FailureMode")

    with pytest.raises(ValueError, match="exactly one FailureMode"):
        _assess(runtime, [failure_id])

    runtime = _runtime()
    _equipment(runtime, "EQ-1")
    event = OntologyObject(
        id="F-NOMODE",
        type="FailureEvent",
        name="Failure",
        properties={"startTime": "2026-10-10T04:00:00+00:00"},
    )
    runtime.upsert_object(event)
    _rel(runtime, "failureOfEquipment", event.id, event.type, "EQ-1", "Equipment")
    with pytest.raises(ValueError, match="exactly one FailureMode"):
        _assess(runtime, [event.id])


def test_analysis_window_requires_ordered_timezone_aware_bounds():
    runtime = _runtime()
    _equipment(runtime, "EQ-1")
    failure_id = _failure(runtime, "F-1", "EQ-1", "FM-X")

    with pytest.raises(ValueError, match="must include timezone context"):
        _assess(runtime, [failure_id], analysis_start=datetime(2026, 10, 1))
    with pytest.raises(ValueError, match="analysis_end must be later"):
        _assess(runtime, [failure_id], analysis_start=END, analysis_end=START)


def test_failure_timestamp_must_be_valid_aware_and_inside_window():
    cases = [
        (None, "must be an ISO-8601 timestamp"),
        (42, "must be an ISO-8601 timestamp"),
        ("not-a-date", "must be an ISO-8601 timestamp"),
        ("2026-10-10T04:00:00", "must include timezone context"),
        ("2026-09-30T23:59:59+00:00", "outside the requested analysis window"),
        ("2026-11-01T00:00:00+00:00", "outside the requested analysis window"),
    ]
    for index, (occurred_at, message) in enumerate(cases):
        runtime = _runtime()
        _equipment(runtime, "EQ-1")
        failure_id = _failure(
            runtime,
            f"F-{index}",
            "EQ-1",
            "FM-X",
            occurred_at=occurred_at,
        )
        with pytest.raises(ValueError, match=message):
            _assess(runtime, [failure_id])


def test_datetime_timestamp_and_no_type_registry_exact_types_are_supported():
    runtime = CEPIORuntime()
    RELIABILITY_FAILURE_PATTERN_IQ_PACK.install(runtime)
    equipment = OntologyObject(id="EQ-1", type="Equipment", name="Equipment")
    mode = OntologyObject(id="FM-1", type="FailureMode", name="Mode")
    event = OntologyObject(
        id="F-1",
        type="FailureEvent",
        name="Failure",
        properties={"startTime": datetime(2026, 10, 10, tzinfo=timezone.utc)},
    )
    for obj in (equipment, mode, event):
        runtime.upsert_object(obj)
    _rel(runtime, "failureOfEquipment", "F-1", "FailureEvent", "EQ-1", "Equipment")
    _rel(runtime, "hasFailureMode", "F-1", "FailureEvent", "FM-1", "FailureMode")

    result = runtime.call_function(
        "assessFailurePatternRecurrence",
        analysis_start=START,
        analysis_end=END,
        failure_event_ids=["F-1"],
        max_expected_events_per_equipment_mode=1,
        max_expected_events_per_failure_mode_population=1,
        min_distinct_equipment_for_systemic=2,
        min_common_cause_events=2,
    )

    assert result.status == FailurePatternStatus.within_expectation


def test_wrong_event_type_and_non_string_cause_fail_closed():
    runtime = _runtime()
    _equipment(runtime, "EQ-1")
    runtime.upsert_object(
        OntologyObject(
            id="NOT-FAIL",
            type="WorkOrder",
            name="Wrong type",
            properties={"startTime": "2026-10-10T04:00:00+00:00"},
        )
    )
    with pytest.raises(ValueError, match="NOT-FAIL is not a FailureEvent"):
        _assess(runtime, ["NOT-FAIL"])

    runtime = _runtime()
    _equipment(runtime, "EQ-1")
    failure_id = _failure(runtime, "F-1", "EQ-1", "FM-X", cause=17)
    with pytest.raises(ValueError, match="cause must be a normalized string"):
        _assess(runtime, [failure_id])


def test_threshold_contract_rejects_invalid_profile_values_before_assessment():
    runtime = _runtime()
    _equipment(runtime, "EQ-1")
    failure_id = _failure(runtime, "F-1", "EQ-1", "FM-X")

    with pytest.raises(ValidationError):
        _assess(runtime, [failure_id], max_expected_events_per_equipment_mode=0)
    with pytest.raises(ValidationError):
        _assess(runtime, [failure_id], max_expected_events_per_failure_mode_population=0)
    with pytest.raises(ValidationError):
        _assess(runtime, [failure_id], min_distinct_equipment_for_systemic=1)
    with pytest.raises(ValidationError):
        _assess(runtime, [failure_id], min_common_cause_events=1)

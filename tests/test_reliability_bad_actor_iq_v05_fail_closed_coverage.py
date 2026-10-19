from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cepio.industry_iq import install_industry_iq_packs
from cepio.model import ObjectRef, OntologyObject, Relationship
from cepio.reliability_bad_actor_iq import RELIABILITY_BAD_ACTOR_FLEET_IQ_PACK
from cepio.runtime import CEPIORuntime


P1_START = datetime(2026, 1, 1, tzinfo=timezone.utc)
P1_END = datetime(2026, 2, 1, tzinfo=timezone.utc)
P2_START = P1_END
P2_END = datetime(2026, 3, 1, tzinfo=timezone.utc)


def _runtime() -> CEPIORuntime:
    runtime = CEPIORuntime()
    install_industry_iq_packs(runtime, [RELIABILITY_BAD_ACTOR_FLEET_IQ_PACK])
    for equipment_id in ("EQ-A", "EQ-B", "EQ-C"):
        runtime.upsert_object(OntologyObject(id=equipment_id, type="Equipment", name=equipment_id))
    runtime.upsert_object(OntologyObject(id="KPI-EXPOSURE", type="KPI", name="Exposure"))
    return runtime


def _add_exposure(
    runtime: CEPIORuntime,
    observation_id: str,
    equipment_id: str,
    *,
    value: object = 1000.0,
    unit: object = "h",
    valid_from: object,
    valid_to: object,
) -> str:
    observation = OntologyObject(
        id=observation_id,
        type="KPIObservation",
        name=observation_id,
        properties={
            "value": value,
            "unitSymbol": unit,
            "validFrom": valid_from,
            "validTo": valid_to,
        },
    )
    runtime.upsert_object(observation)
    runtime.add_relationship(
        Relationship(
            type="observationForEntity",
            source=ObjectRef(id=observation.id, type=observation.type),
            target=ObjectRef(id=equipment_id, type="Equipment"),
        )
    )
    runtime.add_relationship(
        Relationship(
            type="observationOfKPI",
            source=ObjectRef(id=observation.id, type=observation.type),
            target=ObjectRef(id="KPI-EXPOSURE", type="KPI"),
        )
    )
    return observation.id


def _period(start: datetime, end: datetime, observation_ids: dict[str, str]) -> dict[str, object]:
    return {
        "analysis_start": start,
        "analysis_end": end,
        "assets": [
            {
                "equipment_id": equipment_id,
                "exposure_observation_id": observation_ids[equipment_id],
                "failure_event_ids": [],
            }
            for equipment_id in ("EQ-A", "EQ-B", "EQ-C")
        ],
    }


def _valid_periods(
    runtime: CEPIORuntime,
    *,
    first_overrides: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    first_overrides = first_overrides or {}
    p1_observations: dict[str, str] = {}
    p2_observations: dict[str, str] = {}
    for equipment_id in ("EQ-A", "EQ-B", "EQ-C"):
        kwargs = first_overrides if equipment_id == "EQ-A" else {}
        p1_observations[equipment_id] = _add_exposure(
            runtime,
            f"EXP-{equipment_id}-1",
            equipment_id,
            value=kwargs.get("value", 1000.0),
            unit=kwargs.get("unit", "h"),
            valid_from=kwargs.get("valid_from", P1_START.isoformat()),
            valid_to=kwargs.get("valid_to", P1_END.isoformat()),
        )
        p2_observations[equipment_id] = _add_exposure(
            runtime,
            f"EXP-{equipment_id}-2",
            equipment_id,
            valid_from=P2_START.isoformat(),
            valid_to=P2_END.isoformat(),
        )
    return [
        _period(P1_START, P1_END, p1_observations),
        _period(P2_START, P2_END, p2_observations),
    ]


def _assess(runtime: CEPIORuntime, periods: list[dict[str, object]]):
    return runtime.call_function(
        "assessBadActorFleetReliability",
        comparison_context="same-duty-peer-set",
        exposure_kpi_id="KPI-EXPOSURE",
        expected_exposure_unit="h",
        periods=periods,
        exposure_scale=1000.0,
        failure_rate_multiplier=1.5,
        downtime_rate_multiplier=1.5,
        min_failure_events_for_elevation=2,
        min_downtime_hours_for_elevation=1.0,
        min_elevated_periods_for_persistence=2,
    )


def test_string_timestamps_are_parsed_through_the_public_assessment_contract():
    runtime = _runtime()
    result = _assess(runtime, _valid_periods(runtime))
    assert result.persistent_bad_actor_ids == []


@pytest.mark.parametrize(
    ("valid_from", "message"),
    [
        ("not-a-time", "must be an ISO-8601 timestamp"),
        (None, "must be an ISO-8601 timestamp"),
        ("2026-01-01T00:00:00", "must include timezone context"),
    ],
)
def test_malformed_exposure_timestamps_fail_closed(valid_from: object, message: str):
    runtime = _runtime()
    periods = _valid_periods(runtime, first_overrides={"valid_from": valid_from})
    with pytest.raises(ValueError, match=message):
        _assess(runtime, periods)


def test_missing_unit_and_nonnumeric_exposure_fail_closed():
    runtime = _runtime()
    periods = _valid_periods(runtime, first_overrides={"unit": None})
    with pytest.raises(ValueError, match="missing required unitSymbol"):
        _assess(runtime, periods)

    runtime = _runtime()
    periods = _valid_periods(runtime, first_overrides={"value": "1000"})
    with pytest.raises(ValueError, match="missing required numeric value"):
        _assess(runtime, periods)


def test_reversed_exposure_validity_fails_closed():
    runtime = _runtime()
    periods = _valid_periods(
        runtime,
        first_overrides={
            "valid_from": P1_END.isoformat(),
            "valid_to": P1_START.isoformat(),
        },
    )
    with pytest.raises(ValueError, match="invalid exposure validity interval"):
        _assess(runtime, periods)


def _placeholder_period(
    start: datetime, end: datetime, equipment_ids: list[str]
) -> dict[str, object]:
    return {
        "analysis_start": start,
        "analysis_end": end,
        "assets": [
            {
                "equipment_id": equipment_id,
                "exposure_observation_id": f"UNUSED-{index}",
                "failure_event_ids": [],
            }
            for index, equipment_id in enumerate(equipment_ids)
        ],
    }


def test_zero_duration_and_duplicate_periods_fail_before_evidence_resolution():
    runtime = _runtime()
    zero_duration = _placeholder_period(P1_START, P1_START, ["EQ-A", "EQ-B", "EQ-C"])
    later = _placeholder_period(P2_START, P2_END, ["EQ-A", "EQ-B", "EQ-C"])
    with pytest.raises(ValueError, match="positive duration"):
        _assess(runtime, [zero_duration, later])

    runtime = _runtime()
    first = _placeholder_period(P1_START, P1_END, ["EQ-A", "EQ-B", "EQ-C"])
    duplicate = _placeholder_period(P1_START, P1_END, ["EQ-A", "EQ-B", "EQ-C"])
    with pytest.raises(ValueError, match="Duplicate fleet analysis period"):
        _assess(runtime, [first, duplicate])


def test_duplicate_first_peer_population_fails_before_evidence_resolution():
    runtime = _runtime()
    first = _placeholder_period(P1_START, P1_END, ["EQ-A", "EQ-B", "EQ-B"])
    second = _placeholder_period(P2_START, P2_END, ["EQ-A", "EQ-B", "EQ-B"])
    with pytest.raises(ValueError, match="Duplicate equipment in peer population"):
        _assess(runtime, [first, second])

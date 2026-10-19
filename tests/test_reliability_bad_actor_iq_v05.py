from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from cepio.bootstrap import build_runtime
from cepio.industry_iq import install_industry_iq_packs
from cepio.model import ObjectRef, OntologyObject, Relationship
from cepio.reliability_bad_actor_iq import (
    RELIABILITY_BAD_ACTOR_FLEET_IQ_PACK,
    FleetAssetState,
    FleetReviewDisposition,
    PeriodBurdenStatus,
)
from cepio.runtime import CEPIORuntime


P1_START = datetime(2026, 1, 1, tzinfo=timezone.utc)
P1_END = datetime(2026, 2, 1, tzinfo=timezone.utc)
P2_START = P1_END
P2_END = datetime(2026, 3, 1, tzinfo=timezone.utc)
V04_PATH = Path("generalization/industry-iq/reliability-scenarios-v0.4.yaml")
V05_PATH = Path("generalization/industry-iq/reliability-scenarios-v0.5.yaml")


def _runtime(*, types: dict[str, str] | None = None, bare: bool = False):
    runtime = CEPIORuntime() if bare else build_runtime()
    install_industry_iq_packs(runtime, [RELIABILITY_BAD_ACTOR_FLEET_IQ_PACK])
    for equipment_id, equipment_type in (types or {"EQ-A": "Equipment", "EQ-B": "Equipment", "EQ-C": "Equipment"}).items():
        runtime.upsert_object(OntologyObject(id=equipment_id, type=equipment_type, name=equipment_id))
    runtime.upsert_object(OntologyObject(id="KPI-EXPOSURE", type="KPI", name="Service exposure"))
    return runtime


def _exposure(
    runtime,
    observation_id: str,
    equipment_id: str,
    *,
    value: object = 1000.0,
    unit: object = "h",
    valid_from: object = P1_START,
    valid_to: object = P1_END,
    kpi_id: str = "KPI-EXPOSURE",
    observation_type: str = "KPIObservation",
    link_entity: bool = True,
    link_kpi: bool = True,
):
    obs = OntologyObject(
        id=observation_id,
        type=observation_type,
        name=observation_id,
        properties={"value": value, "unitSymbol": unit, "validFrom": valid_from, "validTo": valid_to},
    )
    runtime.upsert_object(obs)
    if link_entity:
        runtime.add_relationship(
            Relationship(
                type="observationForEntity",
                source=ObjectRef(id=obs.id, type=obs.type),
                target=ObjectRef(id=equipment_id, type=runtime.get_object(equipment_id).type),
            )
        )
    if link_kpi:
        runtime.add_relationship(
            Relationship(
                type="observationOfKPI",
                source=ObjectRef(id=obs.id, type=obs.type),
                target=ObjectRef(id=kpi_id, type=runtime.get_object(kpi_id).type),
            )
        )
    return obs.id


def _failure(
    runtime,
    failure_id: str,
    equipment_id: str,
    *,
    start_time: object,
    downtime_hours: object = 1.0,
    failure_type: str = "FailureEvent",
    link: bool = True,
):
    event = OntologyObject(
        id=failure_id,
        type=failure_type,
        name=failure_id,
        properties={"startTime": start_time, "downtimeHours": downtime_hours},
    )
    runtime.upsert_object(event)
    if link:
        runtime.add_relationship(
            Relationship(
                type="failureOfEquipment",
                source=ObjectRef(id=event.id, type=event.type),
                target=ObjectRef(id=equipment_id, type=runtime.get_object(equipment_id).type),
            )
        )
    return event.id


def _period(runtime, start, end, counts, *, exposures=None, downtime=1.0, suffix="1"):
    assets = []
    exposures = exposures or {key: 1000.0 for key in counts}
    for equipment_id, count in counts.items():
        obs_id = _exposure(
            runtime,
            f"EXP-{equipment_id}-{suffix}",
            equipment_id,
            value=exposures[equipment_id],
            valid_from=start,
            valid_to=end,
        )
        failures = [
            _failure(
                runtime,
                f"F-{equipment_id}-{suffix}-{index}",
                equipment_id,
                start_time=start + timedelta(hours=24 + index),
                downtime_hours=downtime,
            )
            for index in range(count)
        ]
        assets.append(
            {
                "equipment_id": equipment_id,
                "exposure_observation_id": obs_id,
                "failure_event_ids": failures,
            }
        )
    return {"analysis_start": start, "analysis_end": end, "assets": assets}


def _assess(runtime, periods, **overrides):
    payload = {
        "comparison_context": "same-duty-pump-cohort",
        "exposure_kpi_id": "KPI-EXPOSURE",
        "expected_exposure_unit": "h",
        "periods": periods,
        "exposure_scale": 1000.0,
        "failure_rate_multiplier": 1.5,
        "downtime_rate_multiplier": 1.5,
        "min_failure_events_for_elevation": 2,
        "min_downtime_hours_for_elevation": 1.0,
        "min_elevated_periods_for_persistence": 2,
    }
    payload.update(overrides)
    return runtime.call_function("assessBadActorFleetReliability", **payload)


def _persistent_fixture(runtime):
    p1 = _period(runtime, P1_START, P1_END, {"EQ-A": 4, "EQ-B": 1, "EQ-C": 1}, suffix="1")
    p2 = _period(runtime, P2_START, P2_END, {"EQ-A": 3, "EQ-B": 1, "EQ-C": 1}, suffix="2")
    return [p1, p2]


def test_v05_promotes_rel_iq_005_without_mutating_frozen_v04():
    v04 = yaml.safe_load(V04_PATH.read_text(encoding="utf-8"))
    v05 = yaml.safe_load(V05_PATH.read_text(encoding="utf-8"))
    old = {item["id"]: item for item in v04["scenarios"]}
    new = {item["id"]: item for item in v05["scenarios"]}
    assert v05["version"] == "0.5"
    assert v05["frozen"] is True
    for scenario_id in ("REL-IQ-001", "REL-IQ-002", "REL-IQ-003", "REL-IQ-004"):
        assert new[scenario_id] == old[scenario_id]
    assert old["REL-IQ-005"]["status"] == "planned"
    assert new["REL-IQ-005"]["status"] == "executable-v0.5"
    assert new["REL-IQ-005"]["pack_id"] == "cepio.iq.reliability.bad-actor-fleet"
    assert v05["rules"]["bad_actor_is_canonical_asset_class"] is False
    assert v05["rules"]["single_period_can_prove_persistent_bad_actor"] is False


def test_pack_is_optional_industry_iq_not_core_default():
    runtime = build_runtime()
    assert runtime.has_function("assessBadActorFleetReliability") is False
    install_industry_iq_packs(runtime, [RELIABILITY_BAD_ACTOR_FLEET_IQ_PACK])
    assert runtime.has_function("assessBadActorFleetReliability") is True
    assert runtime.industry_iq_packs == {"cepio.iq.reliability.bad-actor-fleet": "0.5.0"}


def test_persistent_bad_actor_requires_repeated_normalized_elevation():
    runtime = _runtime()
    result = _assess(runtime, _persistent_fixture(runtime))
    assert result.persistent_bad_actor_ids == ["EQ-A"]
    assert result.watchlist_ids == []
    asset = next(item for item in result.assets if item.equipment_id == "EQ-A")
    assert asset.state == FleetAssetState.persistent_bad_actor
    assert asset.disposition == FleetReviewDisposition.bad_actor_engineering_review
    assert asset.elevated_periods == 2
    assert asset.multi_dimension_periods == 2
    assert all(item.status == PeriodBurdenStatus.elevated_multi_dimension for item in asset.periods)
    assert asset.periods[0].normalized_failure_rate == 4.0
    assert asset.periods[0].normalized_downtime_rate == 4.0
    assert asset.periods[0].peer_median_failure_rate == 1.0
    assert "human bad-actor engineering review" in result.recommendation


def test_single_elevated_period_is_watchlist_not_persistent():
    runtime = _runtime()
    p1 = _period(runtime, P1_START, P1_END, {"EQ-A": 4, "EQ-B": 1, "EQ-C": 1}, suffix="1")
    p2 = _period(runtime, P2_START, P2_END, {"EQ-A": 1, "EQ-B": 1, "EQ-C": 1}, suffix="2")
    result = _assess(runtime, [p1, p2])
    assert result.persistent_bad_actor_ids == []
    assert result.watchlist_ids == ["EQ-A"]
    asset = next(item for item in result.assets if item.equipment_id == "EQ-A")
    assert asset.state == FleetAssetState.watchlist
    assert asset.disposition == FleetReviewDisposition.reliability_review
    assert asset.elevated_periods == 1


def test_raw_failure_count_does_not_override_exposure_normalization():
    runtime = _runtime()
    p1 = _period(
        runtime,
        P1_START,
        P1_END,
        {"EQ-A": 4, "EQ-B": 2, "EQ-C": 2},
        exposures={"EQ-A": 4000.0, "EQ-B": 1000.0, "EQ-C": 1000.0},
        suffix="1",
    )
    p2 = _period(
        runtime,
        P2_START,
        P2_END,
        {"EQ-A": 4, "EQ-B": 2, "EQ-C": 2},
        exposures={"EQ-A": 4000.0, "EQ-B": 1000.0, "EQ-C": 1000.0},
        suffix="2",
    )
    result = _assess(runtime, [p1, p2])
    a = next(item for item in result.assets if item.equipment_id == "EQ-A")
    assert a.periods[0].failure_count == 4
    assert a.periods[0].normalized_failure_rate == 1.0
    assert a.state == FleetAssetState.within_expectation
    assert result.persistent_bad_actor_ids == []


def test_zero_failure_peer_population_remains_deterministic():
    runtime = _runtime()
    p1 = _period(runtime, P1_START, P1_END, {"EQ-A": 0, "EQ-B": 0, "EQ-C": 0}, suffix="1")
    p2 = _period(runtime, P2_START, P2_END, {"EQ-A": 0, "EQ-B": 0, "EQ-C": 0}, suffix="2")
    result = _assess(runtime, [p1, p2])
    assert result.persistent_bad_actor_ids == []
    assert result.watchlist_ids == []
    assert all(asset.state == FleetAssetState.within_expectation for asset in result.assets)


def test_failure_only_and_downtime_only_elevation_are_distinct():
    runtime = _runtime()
    p1 = _period(runtime, P1_START, P1_END, {"EQ-A": 3, "EQ-B": 1, "EQ-C": 1}, downtime=0.0, suffix="1")
    p2 = _period(runtime, P2_START, P2_END, {"EQ-A": 3, "EQ-B": 1, "EQ-C": 1}, downtime=0.0, suffix="2")
    result = _assess(runtime, [p1, p2])
    a = next(item for item in result.assets if item.equipment_id == "EQ-A")
    assert all(item.status == PeriodBurdenStatus.elevated_failure_rate for item in a.periods)

    runtime = _runtime()
    p1 = _period(runtime, P1_START, P1_END, {"EQ-A": 1, "EQ-B": 1, "EQ-C": 1}, suffix="1")
    p2 = _period(runtime, P2_START, P2_END, {"EQ-A": 1, "EQ-B": 1, "EQ-C": 1}, suffix="2")
    for failure_id in ("F-EQ-A-1-0", "F-EQ-A-2-0"):
        failure = runtime.get_object(failure_id)
        failure.properties["downtimeHours"] = 5.0
        runtime.upsert_object(failure)
    result = _assess(runtime, [p1, p2], min_failure_events_for_elevation=2)
    a = next(item for item in result.assets if item.equipment_id == "EQ-A")
    assert all(item.status == PeriodBurdenStatus.elevated_downtime_rate for item in a.periods)


def test_generic_and_drilling_equipment_share_the_same_contract():
    runtime = _runtime(types={"EQ-A": "DrillingEquipment", "EQ-B": "Equipment", "EQ-C": "Equipment"})
    result = _assess(runtime, _persistent_fixture(runtime))
    assert result.persistent_bad_actor_ids == ["EQ-A"]

    runtime = _runtime(bare=True)
    result = _assess(runtime, _persistent_fixture(runtime))
    assert result.persistent_bad_actor_ids == ["EQ-A"]


def test_context_unit_and_kpi_identity_fail_closed():
    runtime = _runtime()
    periods = _persistent_fixture(runtime)
    with pytest.raises(ValueError, match="comparison_context must be non-empty"):
        _assess(runtime, periods, comparison_context=" ")
    with pytest.raises(ValueError, match="expected_exposure_unit must be non-empty"):
        _assess(runtime, periods, expected_exposure_unit=" ")

    runtime = _runtime(bare=True)
    runtime.upsert_object(OntologyObject(id="KPI-EXPOSURE", type="Equipment", name="wrong"))
    periods = _persistent_fixture(runtime)
    with pytest.raises(ValueError, match="KPI-EXPOSURE is not a KPI"):
        _assess(runtime, periods)


def test_periods_must_be_aware_positive_non_overlapping_and_persistence_threshold_must_fit():
    runtime = _runtime()
    p1 = _period(runtime, P1_START, P1_END, {"EQ-A": 1, "EQ-B": 1, "EQ-C": 1}, suffix="1")
    p2 = _period(runtime, P2_START, P2_END, {"EQ-A": 1, "EQ-B": 1, "EQ-C": 1}, suffix="2")
    p2["analysis_start"] = datetime(2026, 2, 1)
    with pytest.raises(ValueError, match="boundaries must include timezone"):
        _assess(runtime, [p1, p2])

    runtime = _runtime()
    p1 = _period(runtime, P1_START, P1_END, {"EQ-A": 1, "EQ-B": 1, "EQ-C": 1}, suffix="1")
    p2 = _period(runtime, P2_START, P2_END, {"EQ-A": 1, "EQ-B": 1, "EQ-C": 1}, suffix="2")
    p2["analysis_start"] = P1_END - timedelta(days=1)
    with pytest.raises(ValueError, match="must not overlap"):
        _assess(runtime, [p1, p2])

    runtime = _runtime()
    periods = _persistent_fixture(runtime)
    with pytest.raises(ValueError, match="Persistence threshold cannot exceed"):
        _assess(runtime, periods, min_elevated_periods_for_persistence=3)


def test_peer_population_must_be_unique_stable_and_have_at_least_three_assets():
    runtime = _runtime()
    p1 = _period(runtime, P1_START, P1_END, {"EQ-A": 1, "EQ-B": 1, "EQ-C": 1}, suffix="1")
    p2 = _period(runtime, P2_START, P2_END, {"EQ-A": 1, "EQ-B": 1, "EQ-C": 1}, suffix="2")
    p2["assets"][2]["equipment_id"] = "EQ-B"
    with pytest.raises(ValueError, match="same qualified peer equipment population|Duplicate equipment"):
        _assess(runtime, [p1, p2])

    runtime = _runtime()
    p1 = _period(runtime, P1_START, P1_END, {"EQ-A": 1, "EQ-B": 1, "EQ-C": 1}, suffix="1")
    p2 = _period(runtime, P2_START, P2_END, {"EQ-A": 1, "EQ-B": 1, "EQ-C": 1}, suffix="2")
    p2["assets"] = p2["assets"][:2]
    with pytest.raises(ValidationError):
        _assess(runtime, [p1, p2])


def test_exposure_must_be_scoped_to_equipment_and_configured_kpi():
    runtime = _runtime()
    periods = _persistent_fixture(runtime)
    obs = runtime.get_object("EXP-EQ-A-1")
    runtime.add_relationship(
        Relationship(
            type="observationForEntity",
            source=ObjectRef(id=obs.id, type=obs.type),
            target=ObjectRef(id="EQ-B", type="Equipment"),
        )
    )
    with pytest.raises(ValueError, match="observationForEntity to exactly EQ-A"):
        _assess(runtime, periods)

    runtime = _runtime()
    runtime.upsert_object(OntologyObject(id="KPI-OTHER", type="KPI", name="Other"))
    periods = _persistent_fixture(runtime)
    obs = runtime.get_object("EXP-EQ-A-1")
    runtime.add_relationship(
        Relationship(
            type="observationOfKPI",
            source=ObjectRef(id=obs.id, type=obs.type),
            target=ObjectRef(id="KPI-OTHER", type="KPI"),
        )
    )
    with pytest.raises(ValueError, match="observationOfKPI to exactly KPI-EXPOSURE"):
        _assess(runtime, periods)


def test_exposure_value_unit_validity_and_reuse_fail_closed():
    runtime = _runtime()
    p1 = _period(runtime, P1_START, P1_END, {"EQ-A": 1, "EQ-B": 1, "EQ-C": 1}, suffix="1")
    p2 = _period(runtime, P2_START, P2_END, {"EQ-A": 1, "EQ-B": 1, "EQ-C": 1}, suffix="2")
    obs = runtime.get_object("EXP-EQ-A-1")
    obs.properties["value"] = 0.0
    runtime.upsert_object(obs)
    with pytest.raises(ValueError, match="value must be positive"):
        _assess(runtime, [p1, p2])

    runtime = _runtime()
    periods = _persistent_fixture(runtime)
    obs = runtime.get_object("EXP-EQ-A-1")
    obs.properties["unitSymbol"] = "d"
    runtime.upsert_object(obs)
    with pytest.raises(ValueError, match="does not match governed exposure unit h"):
        _assess(runtime, periods)

    runtime = _runtime()
    periods = _persistent_fixture(runtime)
    obs = runtime.get_object("EXP-EQ-A-1")
    obs.properties["validFrom"] = P1_START + timedelta(hours=1)
    runtime.upsert_object(obs)
    with pytest.raises(ValueError, match="does not cover the complete analysis period"):
        _assess(runtime, periods)

    runtime = _runtime()
    periods = _persistent_fixture(runtime)
    periods[1]["assets"][0]["exposure_observation_id"] = periods[0]["assets"][0]["exposure_observation_id"]
    with pytest.raises(ValueError, match="reused across analysis periods"):
        _assess(runtime, periods)


def test_failure_evidence_must_be_unique_scoped_in_period_and_have_nonnegative_downtime():
    runtime = _runtime()
    periods = _persistent_fixture(runtime)
    periods[0]["assets"][0]["failure_event_ids"].append(periods[0]["assets"][0]["failure_event_ids"][0])
    with pytest.raises(ValueError, match="Duplicate FailureEvent evidence"):
        _assess(runtime, periods)

    runtime = _runtime()
    periods = _persistent_fixture(runtime)
    failure = runtime.get_object("F-EQ-A-1-0")
    runtime.add_relationship(
        Relationship(
            type="failureOfEquipment",
            source=ObjectRef(id=failure.id, type=failure.type),
            target=ObjectRef(id="EQ-B", type="Equipment"),
        )
    )
    with pytest.raises(ValueError, match="failureOfEquipment to exactly EQ-A"):
        _assess(runtime, periods)

    runtime = _runtime()
    periods = _persistent_fixture(runtime)
    failure = runtime.get_object("F-EQ-A-1-0")
    failure.properties["startTime"] = P2_START + timedelta(hours=1)
    runtime.upsert_object(failure)
    with pytest.raises(ValueError, match="outside its supplied analysis period"):
        _assess(runtime, periods)

    runtime = _runtime()
    periods = _persistent_fixture(runtime)
    failure = runtime.get_object("F-EQ-A-1-0")
    failure.properties["downtimeHours"] = -1.0
    runtime.upsert_object(failure)
    with pytest.raises(ValueError, match="downtimeHours must be non-negative"):
        _assess(runtime, periods)


def test_failure_reuse_across_periods_fails_closed():
    runtime = _runtime()
    periods = _persistent_fixture(runtime)
    reused = periods[0]["assets"][0]["failure_event_ids"][0]
    periods[1]["assets"][0]["failure_event_ids"].append(reused)
    with pytest.raises(ValueError, match="reused across analysis periods"):
        _assess(runtime, periods)


def test_governed_thresholds_validate_before_execution():
    runtime = _runtime()
    periods = _persistent_fixture(runtime)
    with pytest.raises(ValidationError):
        _assess(runtime, periods, exposure_scale=0)
    with pytest.raises(ValidationError):
        _assess(runtime, periods, failure_rate_multiplier=1.0)
    with pytest.raises(ValidationError):
        _assess(runtime, periods, downtime_rate_multiplier=1.0)
    with pytest.raises(ValidationError):
        _assess(runtime, periods, min_failure_events_for_elevation=0)
    with pytest.raises(ValidationError):
        _assess(runtime, periods, min_downtime_hours_for_elevation=-1.0)

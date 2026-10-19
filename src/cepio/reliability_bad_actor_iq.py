from __future__ import annotations

from datetime import datetime
from enum import Enum
from statistics import median

from pydantic import BaseModel, Field

from .model import OntologyObject
from .runtime import CEPIORuntime


class PeriodBurdenStatus(str, Enum):
    within_peer_range = "WITHIN_PEER_RANGE"
    elevated_failure_rate = "ELEVATED_FAILURE_RATE"
    elevated_downtime_rate = "ELEVATED_DOWNTIME_RATE"
    elevated_multi_dimension = "ELEVATED_MULTI_DIMENSION"


class FleetAssetState(str, Enum):
    within_expectation = "WITHIN_EXPECTATION"
    watchlist = "WATCHLIST"
    persistent_bad_actor = "PERSISTENT_BAD_ACTOR"


class FleetReviewDisposition(str, Enum):
    monitor = "MONITOR"
    reliability_review = "RELIABILITY_REVIEW"
    bad_actor_engineering_review = "BAD_ACTOR_ENGINEERING_REVIEW"


class FleetAssetPeriodInput(BaseModel):
    equipment_id: str
    exposure_observation_id: str
    failure_event_ids: list[str] = Field(default_factory=list)


class FleetReliabilityPeriodInput(BaseModel):
    analysis_start: datetime
    analysis_end: datetime
    assets: list[FleetAssetPeriodInput] = Field(min_length=3)


class FleetBadActorInput(BaseModel):
    comparison_context: str
    exposure_kpi_id: str
    expected_exposure_unit: str
    periods: list[FleetReliabilityPeriodInput] = Field(min_length=2)
    exposure_scale: float = Field(default=1000.0, gt=0)
    failure_rate_multiplier: float = Field(default=1.5, gt=1)
    downtime_rate_multiplier: float = Field(default=1.5, gt=1)
    min_failure_events_for_elevation: int = Field(default=2, ge=1)
    min_downtime_hours_for_elevation: float = Field(default=1.0, ge=0)
    min_elevated_periods_for_persistence: int = Field(default=2, ge=2)


class PeriodAssetBurden(BaseModel):
    analysis_start: datetime
    analysis_end: datetime
    equipment_id: str
    exposure_value: float = Field(gt=0)
    exposure_unit: str
    failure_count: int = Field(ge=0)
    downtime_hours: float = Field(ge=0)
    normalized_failure_rate: float = Field(ge=0)
    normalized_downtime_rate: float = Field(ge=0)
    peer_median_failure_rate: float = Field(ge=0)
    peer_median_downtime_rate: float = Field(ge=0)
    status: PeriodBurdenStatus
    evidence_ids: list[str]


class FleetAssetAssessment(BaseModel):
    equipment_id: str
    evaluated_periods: int = Field(ge=2)
    elevated_periods: int = Field(ge=0)
    multi_dimension_periods: int = Field(ge=0)
    state: FleetAssetState
    disposition: FleetReviewDisposition
    periods: list[PeriodAssetBurden]


class FleetBadActorAssessment(BaseModel):
    comparison_context: str
    exposure_kpi_id: str
    exposure_unit: str
    exposure_scale: float = Field(gt=0)
    failure_rate_multiplier: float = Field(gt=1)
    downtime_rate_multiplier: float = Field(gt=1)
    peer_equipment_ids: list[str]
    assets: list[FleetAssetAssessment]
    persistent_bad_actor_ids: list[str]
    watchlist_ids: list[str]
    evidence_ids: list[str]
    recommendation: str


class _AssetPeriodRecord(BaseModel):
    analysis_start: datetime
    analysis_end: datetime
    equipment_id: str
    exposure_observation_id: str
    exposure_value: float
    failure_event_ids: list[str]
    failure_count: int
    downtime_hours: float
    normalized_failure_rate: float
    normalized_downtime_rate: float


def _is_a(runtime: CEPIORuntime, actual_type: str, expected_type: str) -> bool:
    if runtime.type_registry is None:
        return actual_type == expected_type
    return runtime.type_registry.is_a(actual_type, expected_type)


def _require_type(runtime: CEPIORuntime, object_id: str, expected_type: str) -> OntologyObject:
    obj = runtime.get_object(object_id)
    if not _is_a(runtime, obj.type, expected_type):
        raise ValueError(f"{object_id} is not a {expected_type}")
    return obj


def _aware_datetime(value: object, *, label: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{label} must be an ISO-8601 timestamp") from exc
    else:
        raise ValueError(f"{label} must be an ISO-8601 timestamp")
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include timezone context")
    return parsed


def _numeric_property(
    obj: OntologyObject,
    property_name: str,
    *,
    positive: bool = False,
    non_negative: bool = False,
) -> float:
    value = obj.properties.get(property_name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{obj.id} is missing required numeric {property_name}")
    result = float(value)
    if positive and result <= 0:
        raise ValueError(f"{obj.id} {property_name} must be positive")
    if non_negative and result < 0:
        raise ValueError(f"{obj.id} {property_name} must be non-negative")
    return result


def _require_exact_neighbor(
    runtime: CEPIORuntime,
    *,
    source_id: str,
    relationship_type: str,
    expected_id: str,
    label: str,
) -> None:
    target_ids = sorted({item.id for item in runtime.neighbors(source_id, relationship_type)})
    if target_ids != [expected_id]:
        raise ValueError(
            f"{label} must resolve through {relationship_type} to exactly {expected_id}"
        )


def _qualify_exposure(
    runtime: CEPIORuntime,
    *,
    equipment_id: str,
    exposure_observation_id: str,
    exposure_kpi_id: str,
    expected_unit: str,
    analysis_start: datetime,
    analysis_end: datetime,
) -> float:
    observation = _require_type(runtime, exposure_observation_id, "KPIObservation")
    _require_exact_neighbor(
        runtime,
        source_id=observation.id,
        relationship_type="observationForEntity",
        expected_id=equipment_id,
        label=f"KPIObservation {observation.id}",
    )
    _require_exact_neighbor(
        runtime,
        source_id=observation.id,
        relationship_type="observationOfKPI",
        expected_id=exposure_kpi_id,
        label=f"KPIObservation {observation.id}",
    )

    unit = observation.properties.get("unitSymbol")
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError(f"{observation.id} is missing required unitSymbol")
    if unit.strip() != expected_unit:
        raise ValueError(
            f"{observation.id} unitSymbol {unit.strip()} does not match governed exposure unit {expected_unit}"
        )

    valid_from = _aware_datetime(
        observation.properties.get("validFrom"), label=f"{observation.id} validFrom"
    )
    valid_to = _aware_datetime(
        observation.properties.get("validTo"), label=f"{observation.id} validTo"
    )
    if valid_to <= valid_from:
        raise ValueError(f"{observation.id} has invalid exposure validity interval")
    if valid_from > analysis_start or valid_to < analysis_end:
        raise ValueError(
            f"{observation.id} exposure evidence does not cover the complete analysis period"
        )
    return _numeric_property(observation, "value", positive=True)


def _qualify_failures(
    runtime: CEPIORuntime,
    *,
    equipment_id: str,
    failure_event_ids: list[str],
    analysis_start: datetime,
    analysis_end: datetime,
    globally_seen_failure_ids: set[str],
) -> tuple[int, float, set[str]]:
    if len(failure_event_ids) != len(set(failure_event_ids)):
        raise ValueError(f"Duplicate FailureEvent evidence for equipment {equipment_id}")

    downtime_hours = 0.0
    evidence_ids: set[str] = set()
    for failure_event_id in failure_event_ids:
        if failure_event_id in globally_seen_failure_ids:
            raise ValueError(f"FailureEvent {failure_event_id} is reused across analysis periods")
        failure = _require_type(runtime, failure_event_id, "FailureEvent")
        _require_exact_neighbor(
            runtime,
            source_id=failure.id,
            relationship_type="failureOfEquipment",
            expected_id=equipment_id,
            label=f"FailureEvent {failure.id}",
        )
        start_time = _aware_datetime(
            failure.properties.get("startTime"), label=f"{failure.id} startTime"
        )
        if not analysis_start <= start_time < analysis_end:
            raise ValueError(f"FailureEvent {failure.id} is outside its supplied analysis period")
        downtime_hours += _numeric_property(failure, "downtimeHours", non_negative=True)
        globally_seen_failure_ids.add(failure.id)
        evidence_ids.add(failure.id)
    return len(failure_event_ids), downtime_hours, evidence_ids


def _validate_periods(
    periods: list[FleetReliabilityPeriodInput],
) -> list[FleetReliabilityPeriodInput]:
    for period in periods:
        if period.analysis_start.tzinfo is None or period.analysis_end.tzinfo is None:
            raise ValueError("All analysis period boundaries must include timezone context")

    ordered = sorted(periods, key=lambda item: item.analysis_start)
    seen_ranges: set[tuple[datetime, datetime]] = set()
    previous_end: datetime | None = None
    for period in ordered:
        if period.analysis_end <= period.analysis_start:
            raise ValueError("Each analysis period must have positive duration")
        interval = (period.analysis_start, period.analysis_end)
        if interval in seen_ranges:
            raise ValueError("Duplicate fleet analysis period")
        if previous_end is not None and period.analysis_start < previous_end:
            raise ValueError("Fleet analysis periods must not overlap")
        seen_ranges.add(interval)
        previous_end = period.analysis_end
    return ordered


def _period_status(
    *,
    failure_count: int,
    downtime_hours: float,
    failure_rate: float,
    downtime_rate: float,
    median_failure_rate: float,
    median_downtime_rate: float,
    failure_rate_multiplier: float,
    downtime_rate_multiplier: float,
    min_failure_events: int,
    min_downtime_hours: float,
) -> PeriodBurdenStatus:
    failure_elevated = (
        failure_count >= min_failure_events
        and failure_rate > median_failure_rate * failure_rate_multiplier
    )
    downtime_elevated = (
        downtime_hours >= min_downtime_hours
        and downtime_rate > median_downtime_rate * downtime_rate_multiplier
    )
    if failure_elevated and downtime_elevated:
        return PeriodBurdenStatus.elevated_multi_dimension
    if failure_elevated:
        return PeriodBurdenStatus.elevated_failure_rate
    if downtime_elevated:
        return PeriodBurdenStatus.elevated_downtime_rate
    return PeriodBurdenStatus.within_peer_range


def assess_bad_actor_fleet_reliability(
    *,
    runtime: CEPIORuntime,
    comparison_context: str,
    exposure_kpi_id: str,
    expected_exposure_unit: str,
    periods: list[dict[str, object]],
    exposure_scale: float = 1000.0,
    failure_rate_multiplier: float = 1.5,
    downtime_rate_multiplier: float = 1.5,
    min_failure_events_for_elevation: int = 2,
    min_downtime_hours_for_elevation: float = 1.0,
    min_elevated_periods_for_persistence: int = 2,
) -> FleetBadActorAssessment:
    """Find persistent bad-actor candidates from exposure-normalized peer evidence."""

    if not comparison_context.strip():
        raise ValueError("comparison_context must be non-empty")
    expected_unit = expected_exposure_unit.strip()
    if not expected_unit:
        raise ValueError("expected_exposure_unit must be non-empty")
    _require_type(runtime, exposure_kpi_id, "KPI")

    configured_periods = [FleetReliabilityPeriodInput.model_validate(item) for item in periods]
    ordered_periods = _validate_periods(configured_periods)
    if min_elevated_periods_for_persistence > len(ordered_periods):
        raise ValueError("Persistence threshold cannot exceed the number of supplied periods")

    first_peer_ids = sorted(item.equipment_id for item in ordered_periods[0].assets)
    if len(first_peer_ids) != len(set(first_peer_ids)):
        raise ValueError("Duplicate equipment in peer population")

    seen_exposure_ids: set[str] = set()
    seen_failure_ids: set[str] = set()
    evidence_ids: set[str] = {exposure_kpi_id}
    records_by_period: list[list[_AssetPeriodRecord]] = []

    for period in ordered_periods:
        peer_ids = sorted(item.equipment_id for item in period.assets)
        if peer_ids != first_peer_ids:
            raise ValueError("Every period must use the same qualified peer equipment population")

        period_records: list[_AssetPeriodRecord] = []
        for asset in period.assets:
            equipment = _require_type(runtime, asset.equipment_id, "Equipment")
            if asset.exposure_observation_id in seen_exposure_ids:
                raise ValueError(
                    f"KPIObservation {asset.exposure_observation_id} is reused across analysis periods"
                )
            exposure = _qualify_exposure(
                runtime,
                equipment_id=equipment.id,
                exposure_observation_id=asset.exposure_observation_id,
                exposure_kpi_id=exposure_kpi_id,
                expected_unit=expected_unit,
                analysis_start=period.analysis_start,
                analysis_end=period.analysis_end,
            )
            seen_exposure_ids.add(asset.exposure_observation_id)
            failure_count, downtime_hours, failure_evidence = _qualify_failures(
                runtime,
                equipment_id=equipment.id,
                failure_event_ids=asset.failure_event_ids,
                analysis_start=period.analysis_start,
                analysis_end=period.analysis_end,
                globally_seen_failure_ids=seen_failure_ids,
            )
            failure_rate = failure_count / exposure * exposure_scale
            downtime_rate = downtime_hours / exposure * exposure_scale
            period_records.append(
                _AssetPeriodRecord(
                    analysis_start=period.analysis_start,
                    analysis_end=period.analysis_end,
                    equipment_id=equipment.id,
                    exposure_observation_id=asset.exposure_observation_id,
                    exposure_value=exposure,
                    failure_event_ids=asset.failure_event_ids,
                    failure_count=failure_count,
                    downtime_hours=downtime_hours,
                    normalized_failure_rate=failure_rate,
                    normalized_downtime_rate=downtime_rate,
                )
            )
            evidence_ids.update({equipment.id, asset.exposure_observation_id, *failure_evidence})
        records_by_period.append(period_records)

    assessments_by_equipment: dict[str, list[PeriodAssetBurden]] = {
        equipment_id: [] for equipment_id in first_peer_ids
    }
    for period_records in records_by_period:
        median_failure_rate = median(item.normalized_failure_rate for item in period_records)
        median_downtime_rate = median(item.normalized_downtime_rate for item in period_records)
        for record in period_records:
            status = _period_status(
                failure_count=record.failure_count,
                downtime_hours=record.downtime_hours,
                failure_rate=record.normalized_failure_rate,
                downtime_rate=record.normalized_downtime_rate,
                median_failure_rate=median_failure_rate,
                median_downtime_rate=median_downtime_rate,
                failure_rate_multiplier=failure_rate_multiplier,
                downtime_rate_multiplier=downtime_rate_multiplier,
                min_failure_events=min_failure_events_for_elevation,
                min_downtime_hours=min_downtime_hours_for_elevation,
            )
            assessments_by_equipment[record.equipment_id].append(
                PeriodAssetBurden(
                    analysis_start=record.analysis_start,
                    analysis_end=record.analysis_end,
                    equipment_id=record.equipment_id,
                    exposure_value=record.exposure_value,
                    exposure_unit=expected_unit,
                    failure_count=record.failure_count,
                    downtime_hours=round(record.downtime_hours, 6),
                    normalized_failure_rate=round(record.normalized_failure_rate, 6),
                    normalized_downtime_rate=round(record.normalized_downtime_rate, 6),
                    peer_median_failure_rate=round(median_failure_rate, 6),
                    peer_median_downtime_rate=round(median_downtime_rate, 6),
                    status=status,
                    evidence_ids=sorted(
                        {
                            record.equipment_id,
                            record.exposure_observation_id,
                            *record.failure_event_ids,
                        }
                    ),
                )
            )

    asset_assessments: list[FleetAssetAssessment] = []
    persistent_ids: list[str] = []
    watchlist_ids: list[str] = []
    for equipment_id in first_peer_ids:
        period_assessments = assessments_by_equipment[equipment_id]
        elevated_periods = sum(
            item.status != PeriodBurdenStatus.within_peer_range for item in period_assessments
        )
        multi_dimension_periods = sum(
            item.status == PeriodBurdenStatus.elevated_multi_dimension
            for item in period_assessments
        )
        if elevated_periods >= min_elevated_periods_for_persistence:
            state = FleetAssetState.persistent_bad_actor
            disposition = FleetReviewDisposition.bad_actor_engineering_review
            persistent_ids.append(equipment_id)
        elif elevated_periods > 0:
            state = FleetAssetState.watchlist
            disposition = FleetReviewDisposition.reliability_review
            watchlist_ids.append(equipment_id)
        else:
            state = FleetAssetState.within_expectation
            disposition = FleetReviewDisposition.monitor
        asset_assessments.append(
            FleetAssetAssessment(
                equipment_id=equipment_id,
                evaluated_periods=len(period_assessments),
                elevated_periods=elevated_periods,
                multi_dimension_periods=multi_dimension_periods,
                state=state,
                disposition=disposition,
                periods=period_assessments,
            )
        )

    if persistent_ids:
        recommendation = (
            "Persistent exposure-normalized reliability burden is present; route cited evidence "
            "to human bad-actor engineering review before changing maintenance strategy or capital plans."
        )
    elif watchlist_ids:
        recommendation = (
            "Elevated normalized burden appears in isolated periods; retain affected equipment on a "
            "reliability watchlist and continue governed evidence collection."
        )
    else:
        recommendation = (
            "No equipment shows elevated normalized burden under the configured peer thresholds; "
            "continue governed fleet monitoring."
        )

    return FleetBadActorAssessment(
        comparison_context=comparison_context.strip(),
        exposure_kpi_id=exposure_kpi_id,
        exposure_unit=expected_unit,
        exposure_scale=exposure_scale,
        failure_rate_multiplier=failure_rate_multiplier,
        downtime_rate_multiplier=downtime_rate_multiplier,
        peer_equipment_ids=first_peer_ids,
        assets=asset_assessments,
        persistent_bad_actor_ids=persistent_ids,
        watchlist_ids=watchlist_ids,
        evidence_ids=sorted(evidence_ids),
        recommendation=recommendation,
    )


class ReliabilityBadActorFleetIndustryIQPack:
    pack_id = "cepio.iq.reliability.bad-actor-fleet"
    version = "0.5.0"

    def install(self, runtime: CEPIORuntime) -> None:
        runtime.register_function(
            "assessBadActorFleetReliability",
            assess_bad_actor_fleet_reliability,
            input_model=FleetBadActorInput,
            output_type=FleetBadActorAssessment,
        )


RELIABILITY_BAD_ACTOR_FLEET_IQ_PACK = ReliabilityBadActorFleetIndustryIQPack()

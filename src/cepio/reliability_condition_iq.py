from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from .model import OntologyObject
from .runtime import CEPIORuntime


class ConditionDeviationStatus(str, Enum):
    normal = "NORMAL"
    advisory = "ADVISORY_DEVIATION"
    material = "MATERIAL_DEVIATION"
    critical = "CRITICAL_DEVIATION"


class ConditionTrend(str, Enum):
    stable = "STABLE"
    improving = "IMPROVING"
    deteriorating = "DETERIORATING"
    insufficient_history = "INSUFFICIENT_HISTORY"


class ConditionReviewDisposition(str, Enum):
    monitor = "MONITOR"
    inspection_review = "INSPECTION_REVIEW"
    maintenance_review = "MAINTENANCE_REVIEW"
    risk_review = "RISK_REVIEW"


class MonitoredSignalInput(BaseModel):
    signal_key: str
    observation_ids: list[str] = Field(min_length=1)
    unit_symbol: str
    normal_low: float
    normal_high: float
    advisory_low: float
    advisory_high: float
    material_low: float
    material_high: float
    max_observation_age_hours: float = Field(gt=0)
    trend_epsilon: float = Field(default=0.05, ge=0)


class ConditionMonitoringInput(BaseModel):
    equipment_id: str
    assessment_time: datetime
    signals: list[MonitoredSignalInput] = Field(min_length=1)


class SignalConditionAssessment(BaseModel):
    signal_key: str
    unit_symbol: str
    latest_observation_id: str
    latest_observed_at: datetime
    current_value: float
    status: ConditionDeviationStatus
    trend: ConditionTrend
    normalized_distance_from_normal: float = Field(ge=0)
    evidence_ids: list[str]


class ConditionMonitoringAssessment(BaseModel):
    equipment_id: str
    assessed_at: datetime
    status: ConditionDeviationStatus
    disposition: ConditionReviewDisposition
    signals: list[SignalConditionAssessment]
    evidence_ids: list[str]
    recommendation: str


class _ObservationRecord(BaseModel):
    observation_id: str
    observed_at: datetime
    value: float


_STATUS_ORDER = {
    ConditionDeviationStatus.normal: 0,
    ConditionDeviationStatus.advisory: 1,
    ConditionDeviationStatus.material: 2,
    ConditionDeviationStatus.critical: 3,
}
_DISPOSITION_ORDER = {
    ConditionReviewDisposition.monitor: 0,
    ConditionReviewDisposition.inspection_review: 1,
    ConditionReviewDisposition.maintenance_review: 2,
    ConditionReviewDisposition.risk_review: 3,
}


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


def _numeric_value(observation: OntologyObject) -> float:
    value = observation.properties.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{observation.id} is missing required numeric value")
    return float(value)


def _require_unit(observation: OntologyObject, expected_unit: str) -> None:
    actual = observation.properties.get("unitSymbol")
    if not isinstance(actual, str) or not actual.strip():
        raise ValueError(f"{observation.id} is missing required unitSymbol")
    expected = expected_unit.strip()
    if actual.strip() != expected:
        raise ValueError(
            f"{observation.id} unitSymbol {actual.strip()} does not match governed unit {expected}"
        )


def _validate_envelope(signal: MonitoredSignalInput) -> None:
    if not signal.signal_key.strip():
        raise ValueError("signal_key must be non-empty")
    if not signal.unit_symbol.strip():
        raise ValueError(f"Signal {signal.signal_key} unit_symbol must be non-empty")
    if signal.normal_low >= signal.normal_high:
        raise ValueError(f"Signal {signal.signal_key} normal envelope must have positive width")
    ordered = (
        signal.material_low
        <= signal.advisory_low
        <= signal.normal_low
        < signal.normal_high
        <= signal.advisory_high
        <= signal.material_high
    )
    if not ordered:
        raise ValueError(
            f"Signal {signal.signal_key} envelopes must be nested material >= advisory >= normal"
        )


def _status_for_value(value: float, signal: MonitoredSignalInput) -> ConditionDeviationStatus:
    if signal.normal_low <= value <= signal.normal_high:
        return ConditionDeviationStatus.normal
    if signal.advisory_low <= value <= signal.advisory_high:
        return ConditionDeviationStatus.advisory
    if signal.material_low <= value <= signal.material_high:
        return ConditionDeviationStatus.material
    return ConditionDeviationStatus.critical


def _distance_from_normal(value: float, signal: MonitoredSignalInput) -> float:
    width = signal.normal_high - signal.normal_low
    if value < signal.normal_low:
        return (signal.normal_low - value) / width
    if value > signal.normal_high:
        return (value - signal.normal_high) / width
    return 0.0


def _trend(records: list[_ObservationRecord], signal: MonitoredSignalInput) -> ConditionTrend:
    if len(records) < 2:
        return ConditionTrend.insufficient_history
    previous = _distance_from_normal(records[-2].value, signal)
    current = _distance_from_normal(records[-1].value, signal)
    delta = current - previous
    if delta > signal.trend_epsilon:
        return ConditionTrend.deteriorating
    if delta < -signal.trend_epsilon:
        return ConditionTrend.improving
    return ConditionTrend.stable


def _disposition(
    status: ConditionDeviationStatus, trend: ConditionTrend
) -> ConditionReviewDisposition:
    if status == ConditionDeviationStatus.critical:
        return ConditionReviewDisposition.risk_review
    if status == ConditionDeviationStatus.material:
        if trend == ConditionTrend.deteriorating:
            return ConditionReviewDisposition.risk_review
        return ConditionReviewDisposition.maintenance_review
    if status == ConditionDeviationStatus.advisory:
        if trend == ConditionTrend.deteriorating:
            return ConditionReviewDisposition.maintenance_review
        return ConditionReviewDisposition.inspection_review
    return ConditionReviewDisposition.monitor


def _recommendation(disposition: ConditionReviewDisposition) -> str:
    if disposition == ConditionReviewDisposition.risk_review:
        return (
            "Condition evidence warrants reliability risk review; route cited evidence into "
            "REL-IQ-001 before any governed intervention or action."
        )
    if disposition == ConditionReviewDisposition.maintenance_review:
        return (
            "Condition evidence warrants maintenance review; combine it with failure, work and "
            "risk context in REL-IQ-001 before selecting an intervention."
        )
    if disposition == ConditionReviewDisposition.inspection_review:
        return (
            "Condition evidence warrants inspection review; use REL-IQ-001 to determine whether "
            "a governed inspection or other intervention is justified."
        )
    return "Current condition evidence supports continued monitoring within the governed envelope."


def assess_condition_monitoring(
    *,
    runtime: CEPIORuntime,
    equipment_id: str,
    assessment_time: datetime,
    signals: list[dict[str, object]],
) -> ConditionMonitoringAssessment:
    """Interpret governed condition evidence without taking maintenance authority."""

    if assessment_time.tzinfo is None:
        raise ValueError("assessment_time must include timezone context")
    equipment = _require_type(runtime, equipment_id, "Equipment")
    configured = [MonitoredSignalInput.model_validate(item) for item in signals]

    signal_keys = [item.signal_key.strip() for item in configured]
    if len(signal_keys) != len(set(signal_keys)):
        raise ValueError("Duplicate governed signal_key in condition monitoring input")

    all_observation_ids = [oid for item in configured for oid in item.observation_ids]
    if len(all_observation_ids) != len(set(all_observation_ids)):
        raise ValueError("Duplicate ConditionObservation evidence in condition monitoring input")

    linked_ids = {item.id for item in runtime.neighbors(equipment.id, "hasConditionObservation")}
    assessments: list[SignalConditionAssessment] = []
    evidence_ids: set[str] = {equipment.id}

    for signal in configured:
        _validate_envelope(signal)
        records: list[_ObservationRecord] = []
        seen_times: set[datetime] = set()

        for observation_id in signal.observation_ids:
            observation = _require_type(runtime, observation_id, "ConditionObservation")
            if observation.id not in linked_ids:
                raise ValueError(
                    f"ConditionObservation {observation.id} is not linked to equipment {equipment.id}"
                )
            _require_unit(observation, signal.unit_symbol)
            observed_at = _aware_datetime(
                observation.properties.get("observedAt"),
                label=f"{observation.id} observedAt",
            )
            if observed_at > assessment_time:
                raise ValueError(f"{observation.id} is future evidence at assessment time")
            age_hours = (assessment_time - observed_at).total_seconds() / 3600.0
            if age_hours > signal.max_observation_age_hours:
                raise ValueError(f"{observation.id} is stale for signal {signal.signal_key}")
            if observed_at in seen_times:
                raise ValueError(
                    f"Signal {signal.signal_key} has ambiguous duplicate observation time"
                )
            seen_times.add(observed_at)
            records.append(
                _ObservationRecord(
                    observation_id=observation.id,
                    observed_at=observed_at,
                    value=_numeric_value(observation),
                )
            )
            evidence_ids.add(observation.id)

        records.sort(key=lambda item: item.observed_at)
        latest = records[-1]
        status = _status_for_value(latest.value, signal)
        trend = _trend(records, signal)
        assessments.append(
            SignalConditionAssessment(
                signal_key=signal.signal_key.strip(),
                unit_symbol=signal.unit_symbol.strip(),
                latest_observation_id=latest.observation_id,
                latest_observed_at=latest.observed_at,
                current_value=latest.value,
                status=status,
                trend=trend,
                normalized_distance_from_normal=round(
                    _distance_from_normal(latest.value, signal), 6
                ),
                evidence_ids=[item.observation_id for item in records],
            )
        )

    overall = max(assessments, key=lambda item: _STATUS_ORDER[item.status]).status
    disposition = max(
        (_disposition(item.status, item.trend) for item in assessments),
        key=lambda item: _DISPOSITION_ORDER[item],
    )
    return ConditionMonitoringAssessment(
        equipment_id=equipment.id,
        assessed_at=assessment_time,
        status=overall,
        disposition=disposition,
        signals=assessments,
        evidence_ids=sorted(evidence_ids),
        recommendation=_recommendation(disposition),
    )


class ReliabilityConditionMonitoringIndustryIQPack:
    pack_id = "cepio.iq.reliability.condition-monitoring"
    version = "0.3.0"

    def install(self, runtime: CEPIORuntime) -> None:
        runtime.register_function(
            "assessConditionMonitoring",
            assess_condition_monitoring,
            input_model=ConditionMonitoringInput,
            output_type=ConditionMonitoringAssessment,
        )


RELIABILITY_CONDITION_MONITORING_IQ_PACK = ReliabilityConditionMonitoringIndustryIQPack()

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from .model import OntologyObject
from .runtime import CEPIORuntime


class FailurePatternStatus(str, Enum):
    within_expectation = "WITHIN_EXPECTATION"
    local_recurrence = "LOCAL_RECURRENCE"
    systemic_recurrence = "SYSTEMIC_RECURRENCE"


class ReliabilityStrategyResponse(str, Enum):
    monitor = "MONITOR"
    local_engineering_review = "LOCAL_ENGINEERING_REVIEW"
    systemic_reliability_review = "SYSTEMIC_RELIABILITY_REVIEW"


class CommonCauseEvidence(BaseModel):
    failure_mode_id: str
    cause: str
    event_count: int = Field(ge=2)
    failure_event_ids: list[str]
    equipment_ids: list[str]
    cross_equipment: bool


class FailureModeRecurrencePattern(BaseModel):
    failure_mode_id: str
    event_count: int = Field(ge=1)
    equipment_ids: list[str]
    recurring_equipment_ids: list[str]
    exceeds_population_expectation: bool
    systemic: bool
    common_cause_evidence: list[CommonCauseEvidence]


class FailurePatternInput(BaseModel):
    analysis_start: datetime
    analysis_end: datetime
    failure_event_ids: list[str] = Field(min_length=1)
    max_expected_events_per_equipment_mode: int = Field(ge=1)
    max_expected_events_per_failure_mode_population: int = Field(ge=1)
    min_distinct_equipment_for_systemic: int = Field(ge=2)
    min_common_cause_events: int = Field(ge=2)


class FailurePatternAssessment(BaseModel):
    analysis_start: datetime
    analysis_end: datetime
    status: FailurePatternStatus
    strategy_response: ReliabilityStrategyResponse
    patterns: list[FailureModeRecurrencePattern]
    recurring_equipment_ids: list[str]
    recurring_failure_mode_ids: list[str]
    systemic_failure_mode_ids: list[str]
    common_cause_evidence: list[CommonCauseEvidence]
    evidence_ids: list[str]
    recommendation: str


class _FailureRecord(BaseModel):
    event_id: str
    equipment_id: str
    failure_mode_id: str
    cause: str | None


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


def _normalized_cause(event: OntologyObject) -> str | None:
    value = event.properties.get("cause")
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"FailureEvent {event.id} cause must be a normalized string when present")
    normalized = " ".join(value.split()).strip().upper()
    return normalized or None


def _single_equipment(runtime: CEPIORuntime, event: OntologyObject) -> OntologyObject:
    targets = runtime.neighbors(event.id, "failureOfEquipment")
    for target in targets:
        if not _is_a(runtime, target.type, "Equipment"):
            raise ValueError(
                f"FailureEvent {event.id} failureOfEquipment target {target.id} is not Equipment"
            )
    if len(targets) != 1:
        raise ValueError(f"FailureEvent {event.id} must have exactly one Equipment scope")
    return targets[0]


def _single_failure_mode(runtime: CEPIORuntime, event: OntologyObject) -> OntologyObject:
    modes = runtime.neighbors(event.id, "hasFailureMode")
    for mode in modes:
        if not _is_a(runtime, mode.type, "FailureMode"):
            raise ValueError(
                f"FailureEvent {event.id} hasFailureMode target {mode.id} is not FailureMode"
            )
    if len(modes) != 1:
        raise ValueError(f"FailureEvent {event.id} must have exactly one FailureMode")
    return modes[0]


def _failure_record(
    runtime: CEPIORuntime,
    event_id: str,
    analysis_start: datetime,
    analysis_end: datetime,
) -> tuple[_FailureRecord, set[str]]:
    event = _require_type(runtime, event_id, "FailureEvent")
    occurred_at = _aware_datetime(event.properties.get("startTime"), label=f"{event.id} startTime")
    if occurred_at < analysis_start or occurred_at >= analysis_end:
        raise ValueError(f"FailureEvent {event.id} is outside the requested analysis window")
    equipment = _single_equipment(runtime, event)
    failure_mode = _single_failure_mode(runtime, event)
    return (
        _FailureRecord(
            event_id=event.id,
            equipment_id=equipment.id,
            failure_mode_id=failure_mode.id,
            cause=_normalized_cause(event),
        ),
        {event.id, equipment.id, failure_mode.id},
    )


def _common_causes(
    records: list[_FailureRecord],
    failure_mode_id: str,
    min_common_cause_events: int,
) -> list[CommonCauseEvidence]:
    by_cause: dict[str, list[_FailureRecord]] = defaultdict(list)
    for record in records:
        if record.cause is not None:
            by_cause[record.cause].append(record)

    evidence: list[CommonCauseEvidence] = []
    for cause, supporting in sorted(by_cause.items()):
        if len(supporting) < min_common_cause_events:
            continue
        equipment_ids = sorted({item.equipment_id for item in supporting})
        evidence.append(
            CommonCauseEvidence(
                failure_mode_id=failure_mode_id,
                cause=cause,
                event_count=len(supporting),
                failure_event_ids=sorted(item.event_id for item in supporting),
                equipment_ids=equipment_ids,
                cross_equipment=len(equipment_ids) > 1,
            )
        )
    return evidence


def assess_failure_pattern_recurrence(
    *,
    runtime: CEPIORuntime,
    analysis_start: datetime,
    analysis_end: datetime,
    failure_event_ids: list[str],
    max_expected_events_per_equipment_mode: int,
    max_expected_events_per_failure_mode_population: int,
    min_distinct_equipment_for_systemic: int,
    min_common_cause_events: int,
) -> FailurePatternAssessment:
    """Assess repeated governed failure evidence without inventing root cause or exposure normalization."""

    if analysis_start.tzinfo is None or analysis_end.tzinfo is None:
        raise ValueError("analysis_start and analysis_end must include timezone context")
    if analysis_end <= analysis_start:
        raise ValueError("analysis_end must be later than analysis_start")
    if len(set(failure_event_ids)) != len(failure_event_ids):
        raise ValueError("Duplicate failure_event_ids are not allowed")

    records: list[_FailureRecord] = []
    evidence_ids: set[str] = set()
    for event_id in failure_event_ids:
        record, evidence = _failure_record(runtime, event_id, analysis_start, analysis_end)
        records.append(record)
        evidence_ids.update(evidence)

    by_equipment_mode: dict[tuple[str, str], list[_FailureRecord]] = defaultdict(list)
    by_mode: dict[str, list[_FailureRecord]] = defaultdict(list)
    for record in records:
        by_equipment_mode[(record.equipment_id, record.failure_mode_id)].append(record)
        by_mode[record.failure_mode_id].append(record)

    recurring_pairs = {
        pair
        for pair, pair_records in by_equipment_mode.items()
        if len(pair_records) > max_expected_events_per_equipment_mode
    }
    recurring_equipment_ids = sorted({equipment_id for equipment_id, _ in recurring_pairs})

    patterns: list[FailureModeRecurrencePattern] = []
    recurring_failure_mode_ids: set[str] = {mode_id for _, mode_id in recurring_pairs}
    systemic_failure_mode_ids: set[str] = set()
    all_common_cause_evidence: list[CommonCauseEvidence] = []

    for failure_mode_id, mode_records in sorted(by_mode.items()):
        equipment_ids = sorted({item.equipment_id for item in mode_records})
        recurring_for_mode = sorted(
            equipment_id
            for equipment_id, mode_id in recurring_pairs
            if mode_id == failure_mode_id
        )
        exceeds_population = (
            len(mode_records) > max_expected_events_per_failure_mode_population
        )
        if exceeds_population:
            recurring_failure_mode_ids.add(failure_mode_id)
        systemic = (
            exceeds_population
            and len(equipment_ids) >= min_distinct_equipment_for_systemic
        )
        if systemic:
            systemic_failure_mode_ids.add(failure_mode_id)

        cause_evidence = (
            _common_causes(mode_records, failure_mode_id, min_common_cause_events)
            if failure_mode_id in recurring_failure_mode_ids
            else []
        )
        all_common_cause_evidence.extend(cause_evidence)
        patterns.append(
            FailureModeRecurrencePattern(
                failure_mode_id=failure_mode_id,
                event_count=len(mode_records),
                equipment_ids=equipment_ids,
                recurring_equipment_ids=recurring_for_mode,
                exceeds_population_expectation=exceeds_population,
                systemic=systemic,
                common_cause_evidence=cause_evidence,
            )
        )

    systemic_ids = sorted(systemic_failure_mode_ids)
    recurring_mode_ids = sorted(recurring_failure_mode_ids)
    if systemic_ids:
        status = FailurePatternStatus.systemic_recurrence
        strategy_response = ReliabilityStrategyResponse.systemic_reliability_review
        recommendation = (
            "Systemic recurrence exceeds the governed population expectation across multiple equipment. "
            "Route the cited failure-mode and repeated cause evidence to human reliability-strategy review; "
            "recorded common cause is supporting evidence, not proven root cause."
        )
    elif recurring_mode_ids:
        status = FailurePatternStatus.local_recurrence
        strategy_response = ReliabilityStrategyResponse.local_engineering_review
        recommendation = (
            "Local recurrence exceeds the governed equipment/failure-mode expectation. Route the cited "
            "equipment and failure evidence to human reliability engineering review; do not infer a fleet-wide "
            "bad-actor conclusion without exposure normalization."
        )
    else:
        status = FailurePatternStatus.within_expectation
        strategy_response = ReliabilityStrategyResponse.monitor
        recommendation = (
            "Observed failures remain within the governed recurrence expectations for this analysis window."
        )

    return FailurePatternAssessment(
        analysis_start=analysis_start,
        analysis_end=analysis_end,
        status=status,
        strategy_response=strategy_response,
        patterns=patterns,
        recurring_equipment_ids=recurring_equipment_ids,
        recurring_failure_mode_ids=recurring_mode_ids,
        systemic_failure_mode_ids=systemic_ids,
        common_cause_evidence=all_common_cause_evidence,
        evidence_ids=sorted(evidence_ids),
        recommendation=recommendation,
    )


class ReliabilityFailurePatternIndustryIQPack:
    pack_id = "cepio.iq.reliability.failure-pattern-recurrence"
    version = "0.2.0"

    def install(self, runtime: CEPIORuntime) -> None:
        runtime.register_function(
            "assessFailurePatternRecurrence",
            assess_failure_pattern_recurrence,
            input_model=FailurePatternInput,
            output_type=FailurePatternAssessment,
        )


RELIABILITY_FAILURE_PATTERN_IQ_PACK = ReliabilityFailurePatternIndustryIQPack()

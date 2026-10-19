from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

from .model import OntologyObject
from .runtime import CEPIORuntime


class LifeEstimateState(str, Enum):
    current = "CURRENT"
    expiring_soon = "EXPIRING_SOON"


class MaintenanceWindowCompatibility(str, Enum):
    safe = "WINDOW_SAFE"
    margin_low = "WINDOW_MARGIN_LOW"
    after_conservative_horizon = "WINDOW_AFTER_CONSERVATIVE_HORIZON"
    no_qualified_window = "NO_QUALIFIED_WINDOW"


class RULReviewDisposition(str, Enum):
    monitor = "MONITOR"
    plan_maintenance_review = "PLAN_MAINTENANCE_REVIEW"
    accelerate_maintenance_review = "ACCELERATE_MAINTENANCE_REVIEW"
    risk_review = "RISK_REVIEW"


class RULMaintenanceWindowInput(BaseModel):
    equipment_id: str
    assessment_time: datetime
    estimate_id: str
    expected_unit_symbol: str
    lower_remaining_life_hours: float = Field(gt=0)
    upper_remaining_life_hours: float = Field(gt=0)
    work_order_ids: list[str] = Field(default_factory=list)
    estimate_expiry_warning_hours: float = Field(default=24.0, ge=0)
    minimum_completion_margin_hours: float = Field(default=24.0, ge=0)
    maintenance_planning_horizon_hours: float = Field(default=168.0, gt=0)


class MaintenanceWindowAssessment(BaseModel):
    work_order_id: str
    scheduled_start: datetime
    scheduled_end: datetime
    completion_offset_hours: float = Field(ge=0)
    conservative_margin_hours: float
    compatibility: MaintenanceWindowCompatibility


class RULMaintenanceWindowAssessment(BaseModel):
    equipment_id: str
    assessed_at: datetime
    estimate_id: str
    estimate_state: LifeEstimateState
    estimate_valid_to: datetime
    confidence: float = Field(ge=0, le=1)
    lower_remaining_life_hours: float = Field(gt=0)
    central_remaining_life_hours: float = Field(gt=0)
    upper_remaining_life_hours: float = Field(gt=0)
    conservative_horizon_at: datetime
    central_horizon_at: datetime
    optimistic_horizon_at: datetime
    compatibility: MaintenanceWindowCompatibility
    disposition: RULReviewDisposition
    selected_work_order_id: str | None
    windows: list[MaintenanceWindowAssessment]
    evidence_ids: list[str]
    recommendation: str


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


def _numeric_property(obj: OntologyObject, property_name: str, *, positive: bool = False) -> float:
    value = obj.properties.get(property_name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{obj.id} is missing required numeric {property_name}")
    result = float(value)
    if positive and result <= 0:
        raise ValueError(f"{obj.id} {property_name} must be positive")
    return result


def _normalized_unit(obj: OntologyObject, expected_unit: str) -> str:
    actual = obj.properties.get("unitSymbol")
    if not isinstance(actual, str) or not actual.strip():
        raise ValueError(f"{obj.id} is missing required unitSymbol")
    expected = expected_unit.strip()
    if not expected:
        raise ValueError("expected_unit_symbol must be non-empty")
    if actual.strip() != expected:
        raise ValueError(
            f"{obj.id} unitSymbol {actual.strip()} does not match governed unit {expected}"
        )
    return expected


def _qualify_estimate(
    runtime: CEPIORuntime,
    *,
    equipment_id: str,
    estimate_id: str,
    assessment_time: datetime,
    expected_unit_symbol: str,
    lower_hours: float,
    upper_hours: float,
    expiry_warning_hours: float,
) -> tuple[OntologyObject, float, float, datetime, LifeEstimateState]:
    estimate = _require_type(runtime, estimate_id, "RemainingUsefulLifeEstimate")
    targets = runtime.neighbors(estimate.id, "estimatesLifeOf")
    target_ids = sorted({item.id for item in targets})
    if target_ids != [equipment_id]:
        raise ValueError(
            f"RemainingUsefulLifeEstimate {estimate.id} must resolve to exactly equipment {equipment_id}"
        )

    _normalized_unit(estimate, expected_unit_symbol)
    central = _numeric_property(estimate, "remainingUsefulLife", positive=True)
    confidence = _numeric_property(estimate, "confidence")
    if not 0 <= confidence <= 1:
        raise ValueError(f"{estimate.id} confidence must be between 0 and 1")
    if not lower_hours <= central <= upper_hours:
        raise ValueError("RUL uncertainty interval must satisfy lower <= central <= upper")

    valid_from = _aware_datetime(
        estimate.properties.get("validFrom"), label=f"{estimate.id} validFrom"
    )
    valid_to = _aware_datetime(estimate.properties.get("validTo"), label=f"{estimate.id} validTo")
    if valid_to <= valid_from:
        raise ValueError(f"{estimate.id} has invalid validity interval")
    if assessment_time < valid_from:
        raise ValueError(f"{estimate.id} is not yet valid at assessment time")
    if assessment_time >= valid_to:
        raise ValueError(f"{estimate.id} is stale at assessment time")

    remaining_validity_hours = (valid_to - assessment_time).total_seconds() / 3600.0
    state = (
        LifeEstimateState.expiring_soon
        if remaining_validity_hours <= expiry_warning_hours
        else LifeEstimateState.current
    )
    return estimate, central, confidence, valid_to, state


def _window_compatibility(
    *,
    completion_offset_hours: float,
    lower_hours: float,
    minimum_margin_hours: float,
) -> tuple[MaintenanceWindowCompatibility, float]:
    margin = lower_hours - completion_offset_hours
    if margin < 0:
        return MaintenanceWindowCompatibility.after_conservative_horizon, margin
    if margin < minimum_margin_hours:
        return MaintenanceWindowCompatibility.margin_low, margin
    return MaintenanceWindowCompatibility.safe, margin


def _qualify_windows(
    runtime: CEPIORuntime,
    *,
    equipment_id: str,
    assessment_time: datetime,
    work_order_ids: list[str],
    lower_hours: float,
    minimum_margin_hours: float,
) -> tuple[list[MaintenanceWindowAssessment], set[str]]:
    if len(work_order_ids) != len(set(work_order_ids)):
        raise ValueError("Duplicate WorkOrder evidence in RUL maintenance-window assessment")

    linked_ids = {item.id for item in runtime.neighbors(equipment_id, "hasWorkOrder")}
    windows: list[MaintenanceWindowAssessment] = []
    evidence_ids: set[str] = set()
    seen_intervals: set[tuple[datetime, datetime]] = set()

    for work_order_id in work_order_ids:
        work_order = _require_type(runtime, work_order_id, "WorkOrder")
        if work_order.id not in linked_ids:
            raise ValueError(f"WorkOrder {work_order.id} is not linked to equipment {equipment_id}")
        start = _aware_datetime(
            work_order.properties.get("scheduledStart"), label=f"{work_order.id} scheduledStart"
        )
        end = _aware_datetime(
            work_order.properties.get("scheduledEnd"), label=f"{work_order.id} scheduledEnd"
        )
        if end <= start:
            raise ValueError(f"WorkOrder {work_order.id} has invalid scheduled window")
        if start < assessment_time:
            raise ValueError(f"WorkOrder {work_order.id} maintenance window has already started")
        interval = (start, end)
        if interval in seen_intervals:
            raise ValueError("Ambiguous duplicate WorkOrder schedule interval")
        seen_intervals.add(interval)

        completion_offset = (end - assessment_time).total_seconds() / 3600.0
        compatibility, margin = _window_compatibility(
            completion_offset_hours=completion_offset,
            lower_hours=lower_hours,
            minimum_margin_hours=minimum_margin_hours,
        )
        windows.append(
            MaintenanceWindowAssessment(
                work_order_id=work_order.id,
                scheduled_start=start,
                scheduled_end=end,
                completion_offset_hours=round(completion_offset, 6),
                conservative_margin_hours=round(margin, 6),
                compatibility=compatibility,
            )
        )
        evidence_ids.add(work_order.id)

    windows.sort(key=lambda item: (item.scheduled_end, item.scheduled_start, item.work_order_id))
    return windows, evidence_ids


def _select_window(
    windows: list[MaintenanceWindowAssessment],
) -> tuple[MaintenanceWindowCompatibility, str | None]:
    if not windows:
        return MaintenanceWindowCompatibility.no_qualified_window, None
    order = {
        MaintenanceWindowCompatibility.safe: 0,
        MaintenanceWindowCompatibility.margin_low: 1,
        MaintenanceWindowCompatibility.after_conservative_horizon: 2,
    }
    selected = min(windows, key=lambda item: (order[item.compatibility], item.scheduled_end))
    return selected.compatibility, selected.work_order_id


def _disposition(
    *,
    compatibility: MaintenanceWindowCompatibility,
    lower_hours: float,
    planning_horizon_hours: float,
) -> RULReviewDisposition:
    if compatibility == MaintenanceWindowCompatibility.safe:
        return RULReviewDisposition.plan_maintenance_review
    if compatibility == MaintenanceWindowCompatibility.margin_low:
        return RULReviewDisposition.accelerate_maintenance_review
    if compatibility == MaintenanceWindowCompatibility.after_conservative_horizon:
        return RULReviewDisposition.risk_review
    if lower_hours <= planning_horizon_hours:
        return RULReviewDisposition.accelerate_maintenance_review
    return RULReviewDisposition.monitor


def _recommendation(
    disposition: RULReviewDisposition,
    *,
    estimate_state: LifeEstimateState,
) -> str:
    if disposition == RULReviewDisposition.risk_review:
        message = (
            "No supplied maintenance window completes inside the conservative RUL horizon; "
            "route the evidence to human reliability risk review before changing the plan."
        )
    elif disposition == RULReviewDisposition.accelerate_maintenance_review:
        message = (
            "Maintenance timing has low or absent conservative margin; accelerate human planning "
            "review without automatically rescheduling or deferring work."
        )
    elif disposition == RULReviewDisposition.plan_maintenance_review:
        message = (
            "A supplied maintenance window completes inside the conservative RUL horizon; retain "
            "the plan for governed human maintenance review."
        )
    else:
        message = (
            "No maintenance window is required inside the configured planning horizon from the "
            "supplied conservative RUL estimate; continue governed monitoring."
        )
    if estimate_state == LifeEstimateState.expiring_soon:
        message += " Refresh the RUL estimate before its governed validity expires."
    return message


def assess_rul_maintenance_window(
    *,
    runtime: CEPIORuntime,
    equipment_id: str,
    assessment_time: datetime,
    estimate_id: str,
    expected_unit_symbol: str,
    lower_remaining_life_hours: float,
    upper_remaining_life_hours: float,
    work_order_ids: list[str] | None = None,
    estimate_expiry_warning_hours: float = 24.0,
    minimum_completion_margin_hours: float = 24.0,
    maintenance_planning_horizon_hours: float = 168.0,
) -> RULMaintenanceWindowAssessment:
    """Assess RUL evidence against maintenance timing without taking maintenance authority."""

    if assessment_time.tzinfo is None:
        raise ValueError("assessment_time must include timezone context")
    equipment = _require_type(runtime, equipment_id, "Equipment")
    estimate, central, confidence, valid_to, estimate_state = _qualify_estimate(
        runtime,
        equipment_id=equipment.id,
        estimate_id=estimate_id,
        assessment_time=assessment_time,
        expected_unit_symbol=expected_unit_symbol,
        lower_hours=lower_remaining_life_hours,
        upper_hours=upper_remaining_life_hours,
        expiry_warning_hours=estimate_expiry_warning_hours,
    )
    windows, work_evidence = _qualify_windows(
        runtime,
        equipment_id=equipment.id,
        assessment_time=assessment_time,
        work_order_ids=list(work_order_ids or []),
        lower_hours=lower_remaining_life_hours,
        minimum_margin_hours=minimum_completion_margin_hours,
    )
    compatibility, selected_work_order_id = _select_window(windows)
    disposition = _disposition(
        compatibility=compatibility,
        lower_hours=lower_remaining_life_hours,
        planning_horizon_hours=maintenance_planning_horizon_hours,
    )

    return RULMaintenanceWindowAssessment(
        equipment_id=equipment.id,
        assessed_at=assessment_time,
        estimate_id=estimate.id,
        estimate_state=estimate_state,
        estimate_valid_to=valid_to,
        confidence=confidence,
        lower_remaining_life_hours=lower_remaining_life_hours,
        central_remaining_life_hours=central,
        upper_remaining_life_hours=upper_remaining_life_hours,
        conservative_horizon_at=assessment_time + timedelta(hours=lower_remaining_life_hours),
        central_horizon_at=assessment_time + timedelta(hours=central),
        optimistic_horizon_at=assessment_time + timedelta(hours=upper_remaining_life_hours),
        compatibility=compatibility,
        disposition=disposition,
        selected_work_order_id=selected_work_order_id,
        windows=windows,
        evidence_ids=sorted({equipment.id, estimate.id, *work_evidence}),
        recommendation=_recommendation(disposition, estimate_state=estimate_state),
    )


class ReliabilityRULMaintenanceWindowIndustryIQPack:
    pack_id = "cepio.iq.reliability.rul-maintenance-window"
    version = "0.4.0"

    def install(self, runtime: CEPIORuntime) -> None:
        runtime.register_function(
            "assessRULMaintenanceWindow",
            assess_rul_maintenance_window,
            input_model=RULMaintenanceWindowInput,
            output_type=RULMaintenanceWindowAssessment,
        )


RELIABILITY_RUL_MAINTENANCE_WINDOW_IQ_PACK = ReliabilityRULMaintenanceWindowIndustryIQPack()

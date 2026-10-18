from __future__ import annotations

from pydantic import BaseModel, Field

from .runtime import CEPIORuntime


class ProductionLossInput(BaseModel):
    asset_id: str
    hours: float = Field(ge=0)
    unit_margin_per_hour: float = Field(ge=0)


class ProductionExposureInput(BaseModel):
    asset_id: str
    hours: float = Field(ge=0)
    production_rate_per_hour: float = Field(ge=0)


class AssetRiskInput(BaseModel):
    asset_id: str


class MaintenanceDeferralRiskInput(BaseModel):
    equipment_id: str
    work_order_id: str
    risk_id: str
    proposed_deferral_hours: float = Field(ge=0)


class MaintenanceDeferralRiskAssessment(BaseModel):
    risk_id: str
    current_risk_score: float = Field(ge=0, le=1)
    deferral_risk_score: float = Field(ge=0, le=1)
    max_supported_deferral_hours: float = Field(ge=0)
    proposed_deferral_hours: float = Field(ge=0)
    within_supported_window: bool
    hard_constraint: bool


class MarginImpactInput(BaseModel):
    process_unit_id: str
    throughput_delta: float
    margin_per_unit: float


def calculate_production_loss(
    *, runtime: CEPIORuntime, asset_id: str, hours: float, unit_margin_per_hour: float
) -> float:
    runtime.get_object(asset_id)
    return round(hours * unit_margin_per_hour, 2)


def calculate_production_exposure(
    *, runtime: CEPIORuntime, asset_id: str, hours: float, production_rate_per_hour: float
) -> float:
    """Calculate prospective production quantity exposed during an asset-impact window.

    The result is deliberately quantity-neutral: callers supply a rate in their governed
    production unit per hour and receive exposure in that same production unit. Monetary
    consequence remains a separate concern from physical production exposure.
    """
    runtime.get_object(asset_id)
    return round(hours * production_rate_per_hour, 3)


def calculate_asset_risk(*, runtime: CEPIORuntime, asset_id: str) -> float:
    asset = runtime.get_object(asset_id)
    criticality_weight = {
        "low": 0.2,
        "medium": 0.5,
        "high": 0.8,
        "safety_critical": 1.0,
    }.get(str(asset.properties.get("criticality", "medium")), 0.5)
    open_work_orders = len(runtime.neighbors(asset_id, "hasWorkOrder"))
    recent_trips = sum(1 for e in runtime.events_for(asset_id) if e.type == "TripEvent")
    score = min(
        1.0,
        criticality_weight * 0.6 + min(open_work_orders, 5) * 0.05 + min(recent_trips, 5) * 0.05,
    )
    return round(score, 3)


def evaluate_maintenance_deferral_risk(
    *,
    runtime: CEPIORuntime,
    equipment_id: str,
    work_order_id: str,
    risk_id: str,
    proposed_deferral_hours: float,
) -> MaintenanceDeferralRiskAssessment:
    """Evaluate a proposed deferral against governed maintenance-risk evidence.

    CEPIO intentionally does not manufacture an engineering risk model here. The
    linked ``Risk`` object must already contain a current score, the evaluated score
    under deferral, and the maximum supported deferral window. Those values may come
    from an RBI/APM model, operator engineering assessment, or another governed source.
    This function validates graph identity and interprets that evidence fail-closed.
    """

    runtime.get_object(equipment_id)
    runtime.get_object(work_order_id)
    runtime.get_object(risk_id)

    linked_work_orders = {obj.id for obj in runtime.neighbors(equipment_id, "hasWorkOrder")}
    if work_order_id not in linked_work_orders:
        raise ValueError(
            f"WorkOrder {work_order_id} is not linked to equipment {equipment_id} by hasWorkOrder"
        )

    linked_risks = {obj.id for obj in runtime.neighbors(equipment_id, "hasRisk")}
    if risk_id not in linked_risks:
        raise ValueError(f"Risk {risk_id} is not linked to equipment {equipment_id} by hasRisk")

    get_property = getattr(runtime, "get_property", None)

    def property_value(name: str):
        if get_property is not None:
            try:
                return get_property(risk_id, name)
            except KeyError:
                return None
        return runtime.get_object(risk_id).properties.get(name)

    def required_number(name: str) -> float:
        value = property_value(name)
        if value is None:
            raise ValueError(f"Risk {risk_id} is missing required governed property {name}")
        try:
            numeric = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Risk {risk_id} property {name} must be numeric") from exc
        return numeric

    current_score = required_number("currentRiskScore")
    deferral_score = required_number("deferralRiskScore")
    max_hours = required_number("maxSupportedDeferralHours")
    if not 0 <= current_score <= 1:
        raise ValueError("currentRiskScore must be between 0 and 1")
    if not 0 <= deferral_score <= 1:
        raise ValueError("deferralRiskScore must be between 0 and 1")
    if max_hours < 0:
        raise ValueError("maxSupportedDeferralHours must be non-negative")

    hard_constraint = bool(property_value("hardConstraint") or False)
    within_window = (not hard_constraint) and proposed_deferral_hours <= max_hours
    return MaintenanceDeferralRiskAssessment(
        risk_id=risk_id,
        current_risk_score=current_score,
        deferral_risk_score=deferral_score,
        max_supported_deferral_hours=max_hours,
        proposed_deferral_hours=proposed_deferral_hours,
        within_supported_window=within_window,
        hard_constraint=hard_constraint,
    )


def calculate_margin_impact(
    *, runtime: CEPIORuntime, process_unit_id: str, throughput_delta: float, margin_per_unit: float
) -> float:
    runtime.get_object(process_unit_id)
    return round(throughput_delta * margin_per_unit, 2)

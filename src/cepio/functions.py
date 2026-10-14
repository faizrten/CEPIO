from __future__ import annotations

from pydantic import BaseModel, Field

from .runtime import CEPIORuntime


class ProductionLossInput(BaseModel):
    asset_id: str
    hours: float = Field(ge=0)
    unit_margin_per_hour: float = Field(ge=0)


class AssetRiskInput(BaseModel):
    asset_id: str


class MarginImpactInput(BaseModel):
    process_unit_id: str
    throughput_delta: float
    margin_per_unit: float


def calculate_production_loss(
    *, runtime: CEPIORuntime, asset_id: str, hours: float, unit_margin_per_hour: float
) -> float:
    runtime.get_object(asset_id)
    return round(hours * unit_margin_per_hour, 2)


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
        criticality_weight * 0.6
        + min(open_work_orders, 5) * 0.05
        + min(recent_trips, 5) * 0.05,
    )
    return round(score, 3)


def calculate_margin_impact(
    *, runtime: CEPIORuntime, process_unit_id: str, throughput_delta: float, margin_per_unit: float
) -> float:
    runtime.get_object(process_unit_id)
    return round(throughput_delta * margin_per_unit, 2)

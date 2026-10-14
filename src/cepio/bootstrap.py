from __future__ import annotations

from pathlib import Path

from .action_handlers import approve_maintenance_deferral, create_inspection, create_work_order, escalate_risk, require_interface, require_parameter, require_target_type, restore_risk_status
from .functions import AssetRiskInput, MarginImpactInput, ProductionLossInput, calculate_asset_risk, calculate_margin_impact, calculate_production_loss
from .policy import RolePolicyEngine
from .registry import TypeRegistry
from .repositories import InMemoryRepository, SQLiteRepository
from .runtime import CEPIORuntime

ROOT = Path(__file__).resolve().parents[2]


def build_runtime(*, sqlite_path: str | Path | None = None, validate_types: bool = True) -> CEPIORuntime:
    repo = SQLiteRepository(sqlite_path) if sqlite_path is not None else InMemoryRepository()
    registry = TypeRegistry.from_ontology_dir(ROOT / "ontologies") if validate_types else None
    policy = RolePolicyEngine.from_yaml(ROOT / "policies" / "policies.yaml", type_registry=registry)
    runtime = CEPIORuntime(object_repository=repo, event_repository=repo, audit_repository=repo, decision_repository=repo, policy_engine=policy, type_registry=registry)
    runtime.register_action("CreateWorkOrder", create_work_order, {"maintenance_engineer", "maintenance_planner"}, preconditions=[require_interface("MaintainableAsset")])
    runtime.register_action("CreateInspection", create_inspection, {"maintenance_engineer", "reliability_engineer"}, preconditions=[require_interface("Inspectable")])
    runtime.register_action("EscalateRisk", escalate_risk, {"reliability_engineer", "operations_supervisor"}, preconditions=[require_interface("RiskBearing")], compensation_handler=restore_risk_status, compensation_description="Restore the prior riskStatus if downstream workflow execution is rolled back")
    runtime.register_action("ApproveMaintenanceDeferral", approve_maintenance_deferral, {"maintenance_manager", "operations_manager"}, preconditions=[require_target_type("WorkOrder"), require_parameter("reason"), require_parameter("until")], requires_human_approval=True)
    runtime.register_function("calculateProductionLoss", calculate_production_loss, input_model=ProductionLossInput, output_type=float)
    runtime.register_function("calculateAssetRisk", calculate_asset_risk, input_model=AssetRiskInput, output_type=float)
    runtime.register_function("calculateMarginImpact", calculate_margin_impact, input_model=MarginImpactInput, output_type=float)
    return runtime

from __future__ import annotations

from pathlib import Path

from .action_handlers import approve_maintenance_deferral, create_inspection, create_work_order, escalate_risk, require_interface, require_parameter, require_target_type, restore_risk_status
from .contract_runtime import ContractAwareCEPIORuntime
from .functions import AssetRiskInput, MarginImpactInput, ProductionLossInput, calculate_asset_risk, calculate_margin_impact, calculate_production_loss
from .modules import ModuleCatalogue
from .policy import RolePolicyEngine
from .projection import InMemoryProjectionRepository, ProjectionEngine, SQLiteProjectionRepository
from .property_registry import PropertyRegistry
from .provenance import InMemoryProvenanceRepository, SQLiteProvenanceRepository
from .registry import TypeRegistry
from .runtime import CEPIORuntime
from .temporal import TemporalInMemoryRepository, TemporalSQLiteRepository

ROOT = Path(__file__).resolve().parents[2]


def build_runtime(
    *,
    sqlite_path: str | Path | None = None,
    validate_types: bool = True,
    validate_properties: bool = True,
    strict_properties: bool = False,
) -> CEPIORuntime:
    repo = TemporalSQLiteRepository(sqlite_path) if sqlite_path is not None else TemporalInMemoryRepository()
    registry = TypeRegistry.from_ontology_dir(ROOT / "ontologies") if validate_types else None

    property_registry = None
    if validate_properties:
        catalogue = ModuleCatalogue.load(ROOT / "ontology-modules.yaml")
        if not catalogue.property_contract:
            raise ValueError("ontology-modules.yaml does not declare property_contract")
        property_registry = PropertyRegistry.from_yaml(ROOT / catalogue.property_contract)
        property_registry.validate_against_catalogue(catalogue)

    provenance_repository = (
        SQLiteProvenanceRepository(sqlite_path)
        if sqlite_path is not None
        else InMemoryProvenanceRepository()
    )
    policy = RolePolicyEngine.from_yaml(ROOT / "policies" / "policies.yaml", type_registry=registry)
    runtime = ContractAwareCEPIORuntime(
        object_repository=repo,
        event_repository=repo,
        audit_repository=repo,
        decision_repository=repo,
        policy_engine=policy,
        type_registry=registry,
        property_registry=property_registry,
        provenance_repository=provenance_repository,
        strict_properties=strict_properties,
    )
    runtime.register_action("CreateWorkOrder", create_work_order, {"maintenance_engineer", "maintenance_planner"}, preconditions=[require_interface("MaintainableAsset")])
    runtime.register_action("CreateInspection", create_inspection, {"maintenance_engineer", "reliability_engineer"}, preconditions=[require_interface("Inspectable")])
    runtime.register_action("EscalateRisk", escalate_risk, {"reliability_engineer", "operations_supervisor"}, preconditions=[require_interface("RiskBearing")], compensation_handler=restore_risk_status, compensation_description="Restore the prior riskStatus if downstream workflow execution is rolled back")
    runtime.register_action("ApproveMaintenanceDeferral", approve_maintenance_deferral, {"maintenance_manager", "operations_manager"}, preconditions=[require_target_type("WorkOrder"), require_parameter("reason"), require_parameter("until")], requires_human_approval=True)
    runtime.register_function("calculateProductionLoss", calculate_production_loss, input_model=ProductionLossInput, output_type=float)
    runtime.register_function("calculateAssetRisk", calculate_asset_risk, input_model=AssetRiskInput, output_type=float)
    runtime.register_function("calculateMarginImpact", calculate_margin_impact, input_model=MarginImpactInput, output_type=float)
    return runtime


def build_projection_engine(runtime: CEPIORuntime, *, sqlite_path: str | Path | None = None) -> ProjectionEngine:
    checkpoint_repository = (
        SQLiteProjectionRepository(sqlite_path)
        if sqlite_path is not None
        else InMemoryProjectionRepository()
    )
    return ProjectionEngine(
        runtime.object_repository,
        runtime.event_repository,
        checkpoint_repository,
    )

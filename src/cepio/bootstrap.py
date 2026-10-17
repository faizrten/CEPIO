from __future__ import annotations

from pathlib import Path

from rdflib import Graph

from .action_handlers import approve_maintenance_deferral, create_inspection, create_work_order, escalate_risk, require_interface, require_parameter, require_target_type, restore_risk_status
from .config import RuntimeSettings
from .contract_runtime import ContractAwareCEPIORuntime
from .functions import AssetRiskInput, MarginImpactInput, ProductionExposureInput, ProductionLossInput, calculate_asset_risk, calculate_margin_impact, calculate_production_exposure, calculate_production_loss
from .kinetic import InMemoryWorkflowRepository, KineticRuntime, SQLiteWorkflowRepository
from .modules import ModuleCatalogue
from .observability import TelemetrySink, instrument_runtime
from .policy import RolePolicyEngine
from .profiles import ProfileRegistry
from .projection import InMemoryProjectionRepository, ProjectionEngine, SQLiteProjectionRepository
from .property_registry import PropertyRegistry
from .provenance import InMemoryProvenanceRepository, SQLiteProvenanceRepository
from .registry import TypeRegistry
from .resource_paths import resolve_resource_root
from .runtime import CEPIORuntime
from .temporal import TemporalInMemoryRepository, TemporalSQLiteRepository


def build_runtime(
    *,
    sqlite_path: str | Path | None = None,
    validate_types: bool = True,
    validate_properties: bool = True,
    strict_properties: bool = False,
    resource_root: str | Path | None = None,
    ontology_dir: str | Path | None = None,
    profiles: tuple[str, ...] | list[str] = (),
    telemetry_sink: TelemetrySink | None = None,
) -> CEPIORuntime:
    root = resolve_resource_root(resource_root)
    ontology_path = Path(ontology_dir).expanduser().resolve() if ontology_dir else root / "ontologies"
    if not ontology_path.exists():
        raise RuntimeError(f"CEPIO ontology directory does not exist: {ontology_path}")

    catalogue = ModuleCatalogue.load(root / "ontology-modules.yaml")
    selected_profiles = ProfileRegistry(root / "profiles", catalogue).load(profiles) if profiles else []

    registry = None
    if validate_types:
        graph = Graph()
        for path in sorted(ontology_path.glob("*.ttl")):
            graph.parse(path, format="turtle")
        for profile in selected_profiles:
            profile.add_ontology_to_graph(graph)
        registry = TypeRegistry.from_graph(graph)

    repo = TemporalSQLiteRepository(sqlite_path) if sqlite_path is not None else TemporalInMemoryRepository()
    property_registry = None
    if validate_properties:
        if not catalogue.property_contract:
            raise ValueError("ontology-modules.yaml does not declare property_contract")
        property_registry = PropertyRegistry.from_yaml(root / catalogue.property_contract)
        property_registry.validate_against_catalogue(catalogue)

    provenance_repository = (
        SQLiteProvenanceRepository(sqlite_path)
        if sqlite_path is not None
        else InMemoryProvenanceRepository()
    )
    policy = RolePolicyEngine.from_yaml(root / "policies" / "policies.yaml", type_registry=registry)
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
    runtime.register_function("calculateProductionExposure", calculate_production_exposure, input_model=ProductionExposureInput, output_type=float)
    runtime.register_function("calculateAssetRisk", calculate_asset_risk, input_model=AssetRiskInput, output_type=float)
    runtime.register_function("calculateMarginImpact", calculate_margin_impact, input_model=MarginImpactInput, output_type=float)
    runtime.register_decision(
        "maintenance-intervention-recommendation",
        allowed_subject_types={"Equipment"},
        allowed_actions={"CreateWorkOrder", "CreateInspection", "EscalateRisk"},
    )

    runtime.resource_root = root  # type: ignore[attr-defined]
    runtime.module_catalogue = catalogue  # type: ignore[attr-defined]
    runtime.profiles = selected_profiles  # type: ignore[attr-defined]
    runtime.profile_versions = {profile.profile_id: profile.version for profile in selected_profiles}  # type: ignore[attr-defined]
    if telemetry_sink is not None:
        runtime = instrument_runtime(runtime, telemetry_sink)
    return runtime


def build_runtime_from_settings(settings: RuntimeSettings | None = None) -> CEPIORuntime:
    settings = settings or RuntimeSettings.from_env()
    sqlite_path = settings.sqlite_path()
    return build_runtime(
        sqlite_path=sqlite_path,
        validate_types=settings.validate_types,
        validate_properties=settings.validate_properties,
        strict_properties=settings.strict_properties,
        resource_root=settings.resource_root,
        ontology_dir=settings.ontology_dir,
        profiles=settings.profiles,
    )


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


def build_kinetic_runtime(
    runtime: CEPIORuntime,
    *,
    sqlite_path: str | Path | None = None,
) -> KineticRuntime:
    repository = (
        SQLiteWorkflowRepository(sqlite_path)
        if sqlite_path is not None
        else InMemoryWorkflowRepository()
    )
    return KineticRuntime(runtime, repository)

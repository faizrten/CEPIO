from pathlib import Path

import yaml
from rdflib import Graph, Namespace, RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parents[1]
CEPIO = Namespace("https://cepio.org/ontology/core#")
IND = Namespace("https://cepio.org/ontology/industrial#")
ASSET = Namespace("https://cepio.org/ontology/asset#")
HSE = Namespace("https://cepio.org/ontology/hse#")
PROCESS = Namespace("https://cepio.org/ontology/process#")


def _graph(name: str) -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontologies" / name, format="turtle")
    return graph


def test_electrical_equipment_is_reusable_industrial_common_semantics():
    graph = _graph("industrial.ttl")

    assert (IND.ElectricalEquipment, RDF.type, OWL.Class) in graph
    assert (IND.ElectricalEquipment, RDFS.subClassOf, IND.Equipment) in graph
    assert (IND.ElectricMotor, RDF.type, OWL.Class) in graph
    assert (IND.ElectricMotor, RDFS.subClassOf, IND.RotatingEquipment) in graph
    assert (IND.ElectricMotor, RDFS.subClassOf, IND.ElectricalEquipment) in graph
    assert (IND.MotorControlCenter, RDF.type, OWL.Class) in graph
    assert (IND.MotorControlCenter, RDFS.subClassOf, IND.ElectricalEquipment) in graph

    assert (IND.drivesEquipment, RDF.type, OWL.ObjectProperty) in graph
    assert (IND.drivesEquipment, RDFS.domain, IND.ElectricMotor) in graph
    assert (IND.drivesEquipment, RDFS.range, IND.Equipment) in graph
    assert (IND.suppliesPowerTo, RDF.type, OWL.ObjectProperty) in graph
    assert (IND.suppliesPowerTo, RDFS.domain, IND.ElectricalEquipment) in graph
    assert (IND.suppliesPowerTo, RDFS.range, IND.Equipment) in graph

    # The frozen benchmark's literal partOf edge was rejected by triage. The
    # motor is an Equipment specialization, not an instance part of its class.
    assert (IND.ElectricMotor, CEPIO.partOf, IND.Equipment) not in graph


def test_asset_criticality_and_management_plan_are_lifecycle_decision_context():
    graph = _graph("asset.ttl")

    assert (ASSET.AssetCriticality, RDF.type, OWL.Class) in graph
    assert (ASSET.AssetCriticality, RDFS.subClassOf, CEPIO.Measurement) in graph
    assert (ASSET.AssetManagementPlan, RDF.type, OWL.Class) in graph
    assert (ASSET.AssetManagementPlan, RDFS.subClassOf, CEPIO.Document) in graph

    assert (ASSET.criticalityForAsset, RDFS.domain, ASSET.AssetCriticality) in graph
    assert (ASSET.criticalityForAsset, RDFS.range, CEPIO.Asset) in graph
    assert (ASSET.planForAsset, RDFS.domain, ASSET.AssetManagementPlan) in graph
    assert (ASSET.planForAsset, RDFS.range, CEPIO.Asset) in graph
    assert (ASSET.criticalityInformsPlan, RDFS.domain, ASSET.AssetCriticality) in graph
    assert (ASSET.criticalityInformsPlan, RDFS.range, ASSET.AssetManagementPlan) in graph
    assert (ASSET.planAddressesRisk, RDFS.range, CEPIO.Risk) in graph
    assert (ASSET.planTracksKPI, RDFS.range, CEPIO.KPI) in graph


def test_arc_flash_remains_assessment_method_mapping_not_hse_class():
    hse_graph = _graph("hse.ttl")
    assert (HSE.ArcFlashStudy, RDF.type, OWL.Class) not in hse_graph
    assert (HSE.RiskAssessment, RDF.type, OWL.Class) in hse_graph

    mapping = yaml.safe_load((ROOT / "mappings" / "electrical_asset_management_bindings.yaml").read_text())
    packaged_mapping = yaml.safe_load(
        (ROOT / "src" / "cepio" / "resources" / "mappings" / "electrical_asset_management_bindings.yaml").read_text()
    )
    arc_flash = mapping["risk_assessment_mappings"][0]
    motor = mapping["electrical_taxonomy_mappings"][0]

    assert arc_flash["id"] == "ieee-1584-arc-flash-assessment"
    assert arc_flash["canonical_type"] == "https://cepio.org/ontology/hse#RiskAssessment"
    assert arc_flash["target_asset_type"] == "https://cepio.org/ontology/industrial#ElectricalEquipment"
    assert arc_flash["semantics"]["no_dedicated_arc_flash_ontology_class"] is True
    assert motor["canonical_type"] == "https://cepio.org/ontology/industrial#ElectricMotor"
    assert packaged_mapping == mapping


def test_phase5_versions_common_modules_without_reverse_process_dependency():
    catalogue = yaml.safe_load((ROOT / "ontology-modules.yaml").read_text())
    modules = {item["id"]: item for item in catalogue["modules"]}

    assert str(modules["industrial"]["version"]) == "0.2.2"
    assert str(modules["asset"]["version"]) == "0.1.1"
    assert modules["industrial"]["tier"] == "industrial-common"
    assert modules["asset"]["tier"] == "industrial-common"

    industrial_dependencies = {item["module"] for item in modules["industrial"]["depends_on"]}
    asset_dependencies = {item["module"] for item in modules["asset"]["depends_on"]}
    assert industrial_dependencies == {"core"}
    assert asset_dependencies == {"core", "industrial"}

    industrial_text = (ROOT / "ontologies" / "industrial.ttl").read_text(encoding="utf-8")
    asset_text = (ROOT / "ontologies" / "asset.ttl").read_text(encoding="utf-8")
    assert "https://cepio.org/ontology/process#" not in industrial_text
    assert "https://cepio.org/ontology/process#" not in asset_text

    # No process-domain aliases are introduced merely to improve the refinery score.
    process_graph = _graph("process_industry.ttl")
    assert (PROCESS.ElectricMotor, RDF.type, OWL.Class) not in process_graph
    assert (PROCESS.AssetCriticality, RDF.type, OWL.Class) not in process_graph

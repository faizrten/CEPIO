from pathlib import Path

import yaml
from packaging.version import Version
from rdflib import Graph, Namespace, RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parents[1]
CEPIO = Namespace("https://cepio.org/ontology/core#")
IND = Namespace("https://cepio.org/ontology/industrial#")
PROCESS = Namespace("https://cepio.org/ontology/process#")
REL = Namespace("https://cepio.org/ontology/reliability#")


def _graph(name: str) -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontologies" / name, format="turtle")
    return graph


def test_process_variable_is_canonical_without_parallel_padim_device_identity():
    graph = _graph("process_industry.ttl")

    assert (PROCESS.ProcessVariable, RDF.type, OWL.Class) in graph
    assert (PROCESS.ProcessVariable, RDFS.subClassOf, CEPIO.Entity) in graph
    assert (PROCESS.measuresProcessVariable, RDF.type, OWL.ObjectProperty) in graph
    assert (PROCESS.measuresProcessVariable, RDFS.domain, IND.Equipment) in graph
    assert (PROCESS.measuresProcessVariable, RDFS.range, PROCESS.ProcessVariable) in graph

    # PA-DIM device identity and diagnostic terminology remain external mappings.
    assert (PROCESS.ProcessDevice, RDF.type, OWL.Class) not in graph
    assert (PROCESS.DeviceDiagnosticObservation, RDF.type, OWL.Class) not in graph

    mapping = yaml.safe_load((ROOT / "mappings" / "process_instrumentation_bindings.yaml").read_text())
    packaged_mapping = yaml.safe_load(
        (ROOT / "src" / "cepio" / "resources" / "mappings" / "process_instrumentation_bindings.yaml").read_text()
    )
    device = mapping["device_mappings"][0]
    diagnostic = mapping["device_mappings"][1]

    assert device["id"] == "opc-padim-process-device"
    assert device["canonical_type"] == "https://cepio.org/ontology/industrial#Equipment"
    assert device["process_context"]["variable_type"] == "https://cepio.org/ontology/process#ProcessVariable"
    assert device["semantics"]["no_parallel_device_identity"] is True
    assert diagnostic["canonical_type"] == "https://cepio.org/ontology/reliability#ConditionSignal"
    assert diagnostic["observed_asset_relationship"] == "https://cepio.org/ontology/reliability#observedOnEquipment"
    assert packaged_mapping == mapping


def test_piping_segment_is_minimal_physical_topology_for_process_streams():
    graph = _graph("process_industry.ttl")

    assert (PROCESS.PipingSegment, RDF.type, OWL.Class) in graph
    assert (PROCESS.PipingSegment, RDFS.subClassOf, CEPIO.PhysicalAsset) in graph
    assert (PROCESS.carriesStream, RDF.type, OWL.ObjectProperty) in graph
    assert (PROCESS.carriesStream, RDFS.domain, PROCESS.PipingSegment) in graph
    assert (PROCESS.carriesStream, RDFS.range, PROCESS.ProcessStream) in graph

    # Detailed DEXPI/CFIHOS exchange structures are not copied into CEPIO.
    assert (PROCESS.DEXPIPipingSegment, RDF.type, OWL.Class) not in graph
    assert (PROCESS.CFIHOSPipingSegment, RDF.type, OWL.Class) not in graph


def test_namur_noa_channel_remains_an_integration_binding():
    process_graph = _graph("process_industry.ttl")
    core_graph = _graph("core.ttl")

    assert (PROCESS.MonitoringOptimizationChannel, RDF.type, OWL.Class) not in process_graph
    assert (CEPIO.DigitalAsset, RDF.type, OWL.Class) in core_graph
    assert (CEPIO.dependsOn, RDF.type, OWL.ObjectProperty) in core_graph

    mapping = yaml.safe_load((ROOT / "mappings" / "process_instrumentation_bindings.yaml").read_text())
    binding = mapping["integration_bindings"][0]
    assert binding["id"] == "namur-noa-monitoring-optimization-channel"
    assert binding["canonical_type"] == "https://cepio.org/ontology/core#DigitalAsset"
    assert binding["dependency_relationship"] == "https://cepio.org/ontology/core#dependsOn"
    assert binding["source_asset_type"] == "https://cepio.org/ontology/industrial#Equipment"
    assert binding["semantics"]["control_path_unchanged"] is True
    assert binding["semantics"]["deployment_topology_is_external"] is True


def test_phase4_is_additively_versioned_without_new_cross_tier_cycles():
    catalogue = yaml.safe_load((ROOT / "ontology-modules.yaml").read_text())
    modules = {item["id"]: item for item in catalogue["modules"]}

    process_module = modules["process_industry"]
    assert Version(str(process_module["version"])) >= Version("0.1.5")
    assert process_module["tier"] == "domain"
    dependencies = {item["module"] for item in process_module["depends_on"]}
    assert {"core", "industrial", "asset", "kinetic", "manufacturing"}.issubset(dependencies)

    # This slice reuses reliability semantics through mapping only, so no new
    # ontology dependency is required and the industrial-common layer stays
    # independent of process-industry vocabulary.
    assert "reliability" not in dependencies
    reliability_text = (ROOT / "ontologies" / "reliability.ttl").read_text(encoding="utf-8")
    assert "https://cepio.org/ontology/process#" not in reliability_text

from pathlib import Path

import yaml
from rdflib import Graph, Namespace, RDF, RDFS, OWL

ROOT = Path(__file__).resolve().parents[1]
CEPIO = Namespace("https://cepio.org/ontology/core#")
IND = Namespace("https://cepio.org/ontology/industrial#")
PROCESS = Namespace("https://cepio.org/ontology/process#")


def _graph(name: str) -> Graph:
    graph = Graph()
    graph.parse(ROOT / "ontologies" / name, format="turtle")
    return graph


def test_procedure_semantics_are_process_domain_and_reuse_core_execution_contracts():
    process_graph = _graph("process_industry.ttl")
    core_graph = _graph("core.ttl")

    assert (PROCESS.OperatingProcedure, RDF.type, OWL.Class) in process_graph
    assert (PROCESS.OperatingProcedure, RDFS.subClassOf, CEPIO.Document) in process_graph
    assert (PROCESS.ProcedureStep, RDF.type, OWL.Class) in process_graph
    assert (PROCESS.ProcedureStep, RDFS.subClassOf, CEPIO.Entity) in process_graph
    assert (PROCESS.ProcedureExecution, RDF.type, OWL.Class) in process_graph
    assert (PROCESS.ProcedureExecution, RDFS.subClassOf, CEPIO.Activity) in process_graph
    assert (PROCESS.executesProcedure, RDF.type, OWL.ObjectProperty) in process_graph
    assert (PROCESS.executesProcedure, RDFS.domain, PROCESS.ProcedureExecution) in process_graph
    assert (PROCESS.executesProcedure, RDFS.range, PROCESS.OperatingProcedure) in process_graph

    # Work permits, isolations, barriers and other execution gates compose through
    # the existing generic dependency contract; no procedure-specific control edge
    # is introduced.
    assert (CEPIO.dependsOn, RDF.type, OWL.ObjectProperty) in core_graph
    assert (PROCESS.procedureDependsOnPermit, RDF.type, OWL.ObjectProperty) not in process_graph
    assert (PROCESS.procedureDependsOnIsolation, RDF.type, OWL.ObjectProperty) not in process_graph


def test_abnormal_situation_is_process_state_not_alarm_identity():
    process_graph = _graph("process_industry.ttl")
    industrial_graph = _graph("industrial.ttl")

    assert (PROCESS.AbnormalSituation, RDF.type, OWL.Class) in process_graph
    assert (PROCESS.AbnormalSituation, RDFS.subClassOf, CEPIO.State) in process_graph
    assert (IND.Alarm, RDF.type, OWL.Class) in industrial_graph
    assert (PROCESS.Alarm, RDF.type, OWL.Class) not in process_graph


def test_alarm_and_control_semantics_are_reusable_industrial_common():
    graph = _graph("industrial.ttl")

    assert (IND.Alarm, RDF.type, OWL.Class) in graph
    assert (IND.Alarm, RDFS.subClassOf, CEPIO.Event) in graph
    assert (IND.AlarmRationalization, RDF.type, OWL.Class) in graph
    assert (IND.AlarmRationalization, RDFS.subClassOf, CEPIO.Document) in graph
    assert (IND.ControlLoop, RDF.type, OWL.Class) in graph
    assert (IND.ControlLoop, RDFS.subClassOf, CEPIO.FunctionalAsset) in graph

    assert (IND.alarmForState, RDF.type, OWL.ObjectProperty) in graph
    assert (IND.alarmForState, RDFS.domain, IND.Alarm) in graph
    assert (IND.alarmForState, RDFS.range, CEPIO.State) in graph
    assert (IND.rationalizesAlarm, RDF.type, OWL.ObjectProperty) in graph
    assert (IND.rationalizesAlarm, RDFS.domain, IND.AlarmRationalization) in graph
    assert (IND.rationalizesAlarm, RDFS.range, IND.Alarm) in graph


def test_alarm_model_stays_independent_of_process_domain():
    graph = _graph("industrial.ttl")
    text = (ROOT / "ontologies" / "industrial.ttl").read_text(encoding="utf-8")

    assert "https://cepio.org/ontology/process#" not in text
    assert (IND.alarmForState, RDFS.range, PROCESS.AbnormalSituation) not in graph


def test_procedure_alarm_slice_is_additively_versioned():
    catalogue = yaml.safe_load((ROOT / "ontology-modules.yaml").read_text())
    modules = {item["id"]: item for item in catalogue["modules"]}

    assert str(modules["industrial"]["version"]) == "0.2.1"
    assert str(modules["process_industry"]["version"]) == "0.1.2"
    assert modules["industrial"]["tier"] == "industrial-common"
    assert modules["process_industry"]["tier"] == "domain"

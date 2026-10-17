from pathlib import Path

import pytest
import yaml

from cepio.generalization import run_harness
from scripts.build_drilling_domain_qualification_v041 import normalize

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "generalization"
ARCHETYPE = BASE / "archetypes/drilling-contractor-v0.1.yaml"
PERSONAS = BASE / "personas/drilling-contractor-v0.3.yaml"
RAW_COMPETENCY = BASE / "competency/drilling-contractor-domain-qualification-v0.4.yaml"
STANDARDS = BASE / "standards/drilling-references.yaml"


def test_normalized_v041_is_fully_answerable_after_core_remediation(tmp_path):
    source = yaml.safe_load(RAW_COMPETENCY.read_text())
    normalized = normalize(source)
    competency = tmp_path / "drilling-contractor-domain-qualification-v0.4.1.yaml"
    competency.write_text(yaml.safe_dump(normalized, sort_keys=False))

    report = run_harness(ROOT, ARCHETYPE, competency, PERSONAS, STANDARDS)

    assert report["harness_version"] == "0.2"
    assert report["evaluation_contract"] == "capability-alternatives"
    assert report["question_count"] == 15
    assert report["status_counts"] == {"PASS": 15, "PARTIAL": 0, "FAIL": 0, "ERROR": 0}
    assert report["semantic_check_pass_rate"] == pytest.approx(1.0)


def test_remediation_does_not_add_drilling_domain_vocabulary():
    drilling = (ROOT / "ontologies/drilling.ttl").read_text()
    assert "Prediction" not in drilling
    assert "OperationalPlan" not in drilling
    assert "PlanRevision" not in drilling
    assert "OutcomeAssessment" not in drilling


def test_new_common_semantics_live_in_their_owner_modules():
    agentic = (ROOT / "ontologies/agentic_operations.ttl").read_text()
    kinetic = (ROOT / "ontologies/kinetic.ttl").read_text()
    performance = (ROOT / "ontologies/performance.ttl").read_text()

    assert "agentic:Prediction a owl:Class" in agentic
    assert "agentic:supportedByEvidence a owl:ObjectProperty" in agentic
    assert "agentic:predictionFor a owl:ObjectProperty" in agentic
    assert "agentic:predictsRisk a owl:ObjectProperty" in agentic

    assert "kin:OperationalPlan a owl:Class" in kinetic
    assert "kin:PlanRevision a owl:Class" in kinetic
    assert "kin:revisesPlan a owl:ObjectProperty" in kinetic
    assert "kin:authorizesRevision a owl:ObjectProperty" in kinetic

    assert "perf:OutcomeAssessment a owl:Class" in performance
    assert "perf:assessmentOfDecision a owl:ObjectProperty" in performance
    assert "perf:observedOutcome a owl:ObjectProperty" in performance
    assert "perf:considersRisk a owl:ObjectProperty" in performance

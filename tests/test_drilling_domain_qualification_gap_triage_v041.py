from pathlib import Path
import subprocess
import sys

import yaml

from cepio.generalization import load_gap_triage, run_harness

ROOT = Path(__file__).resolve().parents[1]
GAPS = ROOT / "generalization/gaps/drilling-contractor-domain-qualification-v0.4.1.yaml"
RESOLUTIONS = ROOT / "generalization/gaps/drilling-contractor-domain-qualification-v0.4.1-resolutions.yaml"

EXPECTED = {
    "DC-DQ-009": "GAP-DQ-009-PREDICTION-INFERENCE",
    "DC-DQ-011": "GAP-DQ-011-RECOMMENDATION-EVIDENCE",
    "DC-DQ-014": "GAP-DQ-014-OPERATIONAL-PLAN-REVISION",
    "DC-DQ-015": "GAP-DQ-015-OUTCOME-VALUE-ATTRIBUTION",
}


def _active_triage():
    return load_gap_triage(GAPS)


def _resolutions():
    value = yaml.safe_load(RESOLUTIONS.read_text())
    assert isinstance(value, dict)
    return value


def _normalized_report(tmp_path):
    normalized = tmp_path / "qualification-v0.4.1.yaml"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_drilling_domain_qualification_v041.py"),
            "--source",
            str(
                ROOT
                / "generalization/competency/drilling-contractor-domain-qualification-v0.4.yaml"
            ),
            "--out",
            str(normalized),
        ],
        cwd=ROOT,
        check=True,
    )
    return run_harness(
        ROOT,
        ROOT / "generalization/archetypes/drilling-contractor-v0.1.yaml",
        normalized,
        ROOT / "generalization/personas/drilling-contractor-v0.3.yaml",
        ROOT / "generalization/standards/drilling-references.yaml",
    )


def test_active_gap_triage_matches_current_normalized_v041_failures(tmp_path):
    report = _normalized_report(tmp_path)
    active = _active_triage()
    failures = {
        result["id"]
        for result in report["results"]
        if result["status"] in {"PARTIAL", "FAIL"}
    }

    assert report["status_counts"] == {"PASS": 15, "PARTIAL": 0, "FAIL": 0, "ERROR": 0}
    assert failures == set()
    assert active.status == "accepted"
    assert active.decisions == []


def test_resolution_ledger_preserves_the_four_accepted_core_decisions():
    ledger = _resolutions()
    assert ledger["status"] == "implemented"
    assert ledger["source_triage"] == str(GAPS.relative_to(ROOT)).replace("\\", "/")

    resolutions = {item["question_id"]: item for item in ledger["resolutions"]}
    assert {question: item["gap_id"] for question, item in resolutions.items()} == EXPECTED
    assert {item["disposition"] for item in resolutions.values()} == {"CORE"}
    assert {item["status"] for item in resolutions.values()} == {"implemented"}
    assert {item["module"] for item in resolutions.values()} == {
        "agentic_operations",
        "kinetic",
        "performance",
    }


def test_resolution_ledger_records_reusable_semantics_not_drilling_shortcuts():
    ledger = _resolutions()
    semantics = {
        semantic
        for item in ledger["resolutions"]
        for semantic in item.get("implemented_semantics", [])
    }

    assert {
        "agentic:Prediction",
        "agentic:predictionFor",
        "agentic:predictsRisk",
        "agentic:supportedByEvidence",
        "kinetic:OperationalPlan",
        "kinetic:PlanRevision",
        "kinetic:revisesPlan",
        "kinetic:authorizesRevision",
        "performance:OutcomeAssessment",
        "performance:assessmentOfDecision",
        "performance:observedOutcome",
        "performance:considersRisk",
    } <= semantics
    assert not any(value.startswith("drilling:") for value in semantics)

from pathlib import Path

from cepio.generalization import load_pack
from cepio.runtime_coverage import load_runtime_coverage_suite, run_runtime_coverage
from scripts.run_refinery_operating_qualification import run_k201_lighthouse_gate


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "generalization/competency/refinery-operating-abstraction-v0.1.yaml"
SUITE = ROOT / "generalization/runtime/refinery-operating-abstraction-v0.1.yaml"


def test_refinery_operating_abstraction_pack_is_frozen_and_runtime_explicit():
    pack = load_pack(PACK)
    assert pack.id == "refinery-operating-abstraction-v0.1"
    assert pack.frozen is True
    assert [question.id for question in pack.questions] == [
        "ROA-001",
        "ROA-002",
        "ROA-003",
        "ROA-004",
        "ROA-005",
    ]
    assert all(question.runtime.temporal for question in pack.questions)
    assert all(question.runtime.provenance for question in pack.questions)
    assert sum(question.runtime.policy for question in pack.questions) == 4
    assert sum(question.runtime.kinetic for question in pack.questions) == 3


def test_refinery_runtime_suite_covers_every_frozen_question_with_evidence():
    suite = load_runtime_coverage_suite(SUITE)
    assert suite.competency_pack.endswith("refinery-operating-abstraction-v0.1.yaml")
    report = run_runtime_coverage(ROOT, SUITE)
    assert report["question_count"] == 5
    assert report["status_counts"] == {"PASS": 5, "FAIL": 0, "ERROR": 0}
    assert report["runtime_coverage_rate"] == 1.0
    assert all(result["operator_evidence_gate"]["passed"] for result in report["results"])


def test_k201_lighthouse_proves_governed_verified_idempotent_execution():
    result = run_k201_lighthouse_gate()
    assert result["status"] == "PASS"
    assert result["live_source_qualified"] is False
    assert all(result["checks"].values())
    assert result["outcome_id"]
    assert result["external_execution_id"]
    assert result["policy_evidence"]

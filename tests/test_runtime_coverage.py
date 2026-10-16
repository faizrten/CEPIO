from pathlib import Path

from cepio.operational_assurance import EvidenceBundle
from cepio.runtime_coverage import (
    load_runtime_coverage_suite,
    run_runtime_coverage,
    run_runtime_question,
)

ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "generalization/runtime/drilling-contractor-runtime-coverage-v0.5.yaml"


def _report():
    return run_runtime_coverage(ROOT, SUITE)


def test_runtime_coverage_passes_all_14_frozen_questions():
    report = _report()
    assert report["runtime_coverage_version"] == "0.5"
    assert report["mode"] == "deterministic-runtime-evidence-coverage"
    assert report["question_count"] == 14
    assert report["status_counts"] == {"PASS": 14, "FAIL": 0, "ERROR": 0}
    assert report["runtime_coverage_rate"] == 1.0


def test_runtime_coverage_exactly_matches_frozen_v03_pack():
    report = _report()
    assert report["competency_pack"].endswith("drilling-contractor-persona-capabilities-v0.3.yaml")
    assert report["expected_questions"] == [f"DC-PC-{number:03d}" for number in range(1, 15)]
    assert [result["question_id"] for result in report["results"]] == report["expected_questions"]


def test_every_question_emits_runtime_evidence_and_fail_closed_operator_gate():
    report = _report()
    for result in report["results"]:
        bundle = EvidenceBundle.model_validate(result["evidence_bundle"])
        assert result["probe_count"] >= 1
        assert bundle.records
        assert bundle.evidence_ids
        assert result["operator_evidence_gate"] == {
            "supported": "ANSWERED",
            "unsupported": "REJECTED_UNSUPPORTED_EVIDENCE",
            "passed": True,
        }


def test_runtime_probe_failure_cannot_be_hidden_by_fixture_claim_text():
    suite = load_runtime_coverage_suite(SUITE)
    case = suite.questions[0].model_copy(deep=True)
    case.claim = "This prose still sounds correct, but it must not determine pass/fail."
    case.probes[0].expected_ids = ["NONEXISTENT-AUTHORITY"]
    result = run_runtime_question(case, suite.id, ROOT)
    assert result["status"] == "FAIL"
    assert result["probe_results"][0]["status"] == "FAIL"


def test_runtime_suite_is_deterministically_hashed():
    first = _report()
    second = _report()
    assert first["suite_hash"] == second["suite_hash"]

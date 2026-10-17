from pathlib import Path

from cepio.generalization import load_gap_triage

ROOT = Path(__file__).resolve().parents[1]
GAPS = ROOT / "generalization/gaps/drilling-contractor-domain-qualification-v0.4.1.yaml"

EXPECTED = {
    "DC-DQ-009": "GAP-DQ-009-PREDICTION-INFERENCE",
    "DC-DQ-011": "GAP-DQ-011-RECOMMENDATION-EVIDENCE",
    "DC-DQ-014": "GAP-DQ-014-OPERATIONAL-PLAN-REVISION",
    "DC-DQ-015": "GAP-DQ-015-OUTCOME-VALUE-ATTRIBUTION",
}


def _data():
    return load_gap_triage(GAPS)


def test_gap_triage_matches_normalized_v041_failures(tmp_path):
    import subprocess
    import sys

    from cepio.generalization import run_harness

    normalized = tmp_path / "qualification-v0.4.1.yaml"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_drilling_domain_qualification_v041.py"),
            "--source",
            str(ROOT / "generalization/competency/drilling-contractor-domain-qualification-v0.4.yaml"),
            "--out",
            str(normalized),
        ],
        cwd=ROOT,
        check=True,
    )
    report = run_harness(
        ROOT,
        ROOT / "generalization/archetypes/drilling-contractor-v0.1.yaml",
        normalized,
        ROOT / "generalization/personas/drilling-contractor-v0.3.yaml",
        ROOT / "generalization/standards/drilling-references.yaml",
    )
    data = _data()
    decisions = {item.question_id: item for item in data.decisions}
    failures = {
        result["id"]: result
        for result in report["results"]
        if result["status"] in {"PARTIAL", "FAIL"}
    }
    assert report["status_counts"]["ERROR"] == 0
    assert set(decisions) == set(EXPECTED) == set(failures)
    assert {question: decisions[question].id for question in decisions} == EXPECTED
    for question_id, result in failures.items():
        missing = set()
        for capability in result["capability_details"]:
            if not capability["ok"]:
                best = next(
                    pattern for pattern in capability["alternatives"]
                    if pattern["id"] == capability["best_pattern"]
                )
                missing.update(best["missing"])
        assert missing == set(decisions[question_id].missing_semantics)
    assert data.status == "draft"
    assert {item.benchmark_action for item in data.decisions} == {"revise-in-next-frozen-pack"}


def test_all_v041_gaps_are_reusable_core_semantics():
    decisions = _data().decisions
    assert len(decisions) == 4
    assert {item.disposition for item in decisions} == {"CORE"}
    assert {item.replacement_layer for item in decisions} == {"CORE"}
    assert not any(item.disposition in {"DOMAIN", "PROFILE", "MAPPING"} for item in decisions)


def test_remediation_is_owned_by_common_modules_not_drilling():
    owners = {item.owner_module for item in _data().decisions}
    assert owners == {"agentic_operations", "kinetic", "performance"}

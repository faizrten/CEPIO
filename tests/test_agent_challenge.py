from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_module():
    path = ROOT / "scripts/run_agent_challenge_strict.py"
    spec = importlib.util.spec_from_file_location("run_agent_challenge_test_module", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_agent_challenge_reference_harness_passes():
    module = _load_module()
    report = module.run_challenge(
        agent_kind="reference",
        telemetry_points=600,
        waveform_samples=512,
        seed=1701,
    )
    failed = [item["id"] for item in report["details"] if not item["passed"]]
    assert report["total"] == 10
    assert report["passed"] == 10, failed
    assert report["accuracy"] == 1.0
    assert report["evidence_coverage"] == 1.0
    assert report["unsupported_claims"] == 0
    assert report["identity_accuracy"] == 1.0
    assert report["median_tool_calls"] <= 8
    assert report["semantic_abstraction_leakage"] == 0
    assert report["expected_answers_visible_during_answering"] is False
    assert report["direct_source_access"] is False
    assert report["gate_passed"] is True


def test_agent_payload_isolation_contract():
    module = _load_module()
    questions = module._read_json(module.BENCHMARK / "questions.json")
    forbidden = set(questions["rules"]["forbidden_agent_inputs"])
    payload_keys = {"question", "tools", "final_schema"}
    assert not forbidden.intersection(payload_keys)
    assert {tool["name"] for tool in module.CEPIOToolGateway.TOOL_SCHEMAS} == module.APPROVED_TOOLS


def test_scorer_rejects_unsupported_claims():
    module = _load_module()
    expected = {"expected_refs": ["asset-1"], "expected_values": [4.2]}
    answer = {
        "answer": "asset-1 caused 4.2 hours",
        "refs": ["asset-1"],
        "values": [4.2],
        "claims": [{"text": "asset-1 caused 4.2 hours", "supported_by": ["not-a-real-call"]}],
    }
    score = module._score_answer(expected, answer, trace=[])
    assert score["passed"] is True
    assert score["evidence_ok"] is False
    assert score["unsupported_claims"] == 1

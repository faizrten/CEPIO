"""Synthetic-only, offline checks for the Foundry harness G1 comparator."""

from __future__ import annotations

import json

from scripts.compare_foundry_g1_harness import compare_artifacts
from scripts.run_foundry_reliability_g1 import G1_ALLOWED_TOOLS, RELIABILITY_SKILL_ID


def _artifact(*, harness: str | None = None, model: str = "model-v1") -> dict:
    call = {
        "type": "mcp_call",
        "name": "cepio_evaluate_skill",
        "arguments": json.dumps(
            {"invocation": {"skill_id": RELIABILITY_SKILL_ID, "subject": {"id": "K-101"}}}
        ),
        "output": json.dumps(
            {
                "skill_id": RELIABILITY_SKILL_ID,
                "status": "completed",
                "evidence": [{"source_system": "synthetic-pi", "record_id": "K-101-v1"}],
                "decision": {"id": "synthetic-decision-1"},
            }
        ),
    }
    return {
        "gate": "G1",
        "status": "PASS",
        "agent": {"name": "synthetic-agent", "version": "1"},
        "subject_id": "K-101",
        "allowed_tools": list(G1_ALLOWED_TOOLS),
        "failures": [],
        "model": model,
        "harness": harness,
        "response": {"status": "completed", "output": [call]},
    }


def test_good_synthetic_artifacts_only_establish_protocol_comparability() -> None:
    control = _artifact()
    candidate = _artifact(harness="microsoft_copilot_preview")
    report = compare_artifacts(control, candidate)

    assert report["status"] == "PROTOCOL_COMPARABLE"
    assert report["control"]["protocol_pass"] is True
    assert report["candidate"]["protocol_pass"] is True
    assert report["live_g1_qualified"] is False
    assert report["decision_persistence_verified"] is False
    assert report["performance_uplift_established"] is False


def test_invented_persistence_assertion_cannot_qualify_live_g1() -> None:
    control = _artifact()
    candidate = _artifact(harness="microsoft_copilot_preview")
    candidate["verified"] = True
    candidate["decision_persistence_verified"] = True
    candidate["live_g1_qualified"] = True

    report = compare_artifacts(control, candidate)
    assert report["live_g1_qualified"] is False
    assert report["decision_persistence_verified"] is False


def test_both_artifacts_must_contain_actual_structured_mcp_skill_call() -> None:
    control = _artifact()
    candidate = _artifact(harness="microsoft_copilot_preview")
    candidate["response"]["output"] = [{"type": "message", "content": "I called CEPIO"}]

    report = compare_artifacts(control, candidate)
    assert report["status"] == "BLOCKED"
    assert not report["candidate"]["protocol_pass"]


def test_unlisted_tool_is_rejected_even_if_not_one_of_original_two_action_tools() -> None:
    control = _artifact()
    candidate = _artifact(harness="microsoft_copilot_preview")
    candidate["response"]["output"].append(
        {"type": "mcp_call", "name": "direct_sap_write", "output": {"ok": True}}
    )

    report = compare_artifacts(control, candidate)
    assert report["status"] == "BLOCKED"
    assert "Unapproved MCP tool" in str(report["candidate"]["failures"])


def test_model_mismatch_blocks_harness_only_attribution() -> None:
    report = compare_artifacts(
        _artifact(model="model-v1"),
        _artifact(harness="microsoft_copilot_preview", model="model-v2"),
    )
    assert report["status"] == "BLOCKED"
    assert any("Model identities differ" in x for x in report["confounders"])


def test_missing_harness_identity_or_empty_model_fails_closed() -> None:
    report = compare_artifacts(_artifact(model=""), _artifact())
    assert report["status"] == "BLOCKED"
    assert len(report["confounders"]) >= 2


def test_corrupt_artifacts_cannot_get_protocol_credit() -> None:
    report = compare_artifacts(None, "not-json")
    assert report["status"] == "BLOCKED"
    assert report["control"]["protocol_pass"] is False
    assert report["candidate"]["protocol_pass"] is False

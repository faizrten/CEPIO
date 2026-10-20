from __future__ import annotations

import json

from cepio.integrations.microsoft.foundry_qualification import qualify_g1_response


def _skill_call(*, skill_id: str = "cepio.skill.maintenance.assess-maintenance-deferral"):
    evaluation = {
        "status": "completed",
        "evidence": [
            {
                "object_ref": {"id": "OBS-1", "type": "ConditionObservation"},
                "role": "supporting",
            }
        ],
        "decision": {
            "id": "decision-1",
            "decision_type": "maintenance-deferral-decision",
        },
    }
    return {
        "type": "mcp_call",
        "name": "cepio_evaluate_skill",
        "arguments": json.dumps({"invocation": {"skill_id": skill_id}}),
        "output": json.dumps(evaluation),
        "status": "completed",
    }


def test_g1_qualification_passes_from_protocol_evidence():
    payload = {
        "id": "resp-1",
        "output": [
            {"type": "mcp_call", "name": "cepio_get_object", "output": "{}"},
            _skill_call(),
            {"type": "message", "content": [{"type": "output_text", "text": "Done"}]},
        ],
    }

    result = qualify_g1_response(
        payload,
        required_skill_id="cepio.skill.maintenance.assess-maintenance-deferral",
    )

    assert result.passed is True
    assert result.skill_evaluation_count == 1
    assert result.decision_ids == ("decision-1",)
    assert result.evidence_count == 1
    assert result.to_dict() == {
        "passed": True,
        "reasons": [],
        "tool_names": ["cepio_get_object", "cepio_evaluate_skill"],
        "skill_evaluation_count": 1,
        "decision_ids": ["decision-1"],
        "evidence_count": 1,
    }


def test_g1_qualification_rejects_execution_even_when_skill_succeeds():
    payload = {
        "output": [
            _skill_call(),
            {
                "type": "mcp_call",
                "name": "cepio_execute_action",
                "arguments": "{}",
                "output": "{}",
            },
        ]
    }

    result = qualify_g1_response(payload)

    assert result.passed is False
    assert "external action execution tool was invoked" in result.reasons


def test_g1_qualification_rejects_model_prose_without_skill_protocol_evidence():
    payload = {
        "output": [
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": "I evaluated the Skill and created Decision decision-1.",
                    }
                ],
            }
        ]
    }

    result = qualify_g1_response(payload)

    assert result.passed is False
    assert "no cepio_evaluate_skill MCP call was observed" in result.reasons


def test_g1_qualification_requires_named_skill_when_requested():
    result = qualify_g1_response(
        {"output": [_skill_call(skill_id="other.skill")]},
        required_skill_id="required.skill",
    )

    assert result.passed is False
    assert "required Skill was not invoked: required.skill" in result.reasons


def test_g1_qualification_rejects_incomplete_skill_output_and_malformed_json():
    payload = {
        "output": [
            {
                "type": "mcp_call",
                "name": "cepio_evaluate_skill",
                "arguments": "{not-valid-json",
                "output": json.dumps(
                    {
                        "status": "completed",
                        "decision": None,
                        "evidence": [],
                        "diagnostic": ["scalar", 7],
                    }
                ),
            }
        ]
    }

    result = qualify_g1_response(payload, required_skill_id="required.skill")

    assert result.passed is False
    assert result.decision_ids == ()
    assert result.evidence_count == 0
    assert "required Skill was not invoked: required.skill" in result.reasons
    assert "no persisted CEPIO Decision identity was found in Skill output" in result.reasons
    assert "Skill output contained no governed evidence references" in result.reasons

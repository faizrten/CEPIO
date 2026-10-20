from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FoundryG1Qualification:
    passed: bool
    reasons: tuple[str, ...]
    tool_names: tuple[str, ...]
    skill_evaluation_count: int
    decision_ids: tuple[str, ...]
    evidence_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "reasons": list(self.reasons),
            "tool_names": list(self.tool_names),
            "skill_evaluation_count": self.skill_evaluation_count,
            "decision_ids": list(self.decision_ids),
            "evidence_count": self.evidence_count,
        }


def _decode_jsonish(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "[{":
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def _walk(value: Any):
    value = _decode_jsonish(value)
    yield value
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk(item)


def _mcp_calls(payload: Any) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for item in _walk(payload):
        if isinstance(item, dict) and item.get("type") == "mcp_call" and item.get("name"):
            calls.append(item)
    return calls


def _skill_evaluation(value: Any) -> dict[str, Any] | None:
    for item in _walk(value):
        if not isinstance(item, dict):
            continue
        decision = item.get("decision")
        evidence = item.get("evidence")
        if (
            isinstance(decision, dict)
            and isinstance(evidence, list)
            and item.get("status") in {"completed", "COMPLETED"}
        ):
            return item
    return None


def qualify_g1_response(
    payload: Any,
    *,
    required_skill_id: str | None = None,
) -> FoundryG1Qualification:
    """Qualify the bounded Foundry→CEPIO G1 response contract.

    The check is deliberately based on protocol evidence, not the model's prose:
    - the agent must actually call ``cepio_evaluate_skill``;
    - it must not call ``cepio_execute_action``;
    - the Skill result must contain persisted Decision identity and evidence;
    - an optional required Skill identity must be present in the MCP invocation.
    """

    calls = _mcp_calls(payload)
    tool_names = tuple(str(call["name"]) for call in calls)
    reasons: list[str] = []

    if "cepio_execute_action" in tool_names:
        reasons.append("external action execution tool was invoked")

    skill_calls = [call for call in calls if call.get("name") == "cepio_evaluate_skill"]
    if not skill_calls:
        reasons.append("no cepio_evaluate_skill MCP call was observed")

    decision_ids: list[str] = []
    evidence_count = 0
    matched_required_skill = required_skill_id is None

    for call in skill_calls:
        arguments = _decode_jsonish(call.get("arguments"))
        if required_skill_id and isinstance(arguments, dict):
            invocation = arguments.get("invocation")
            if isinstance(invocation, dict) and invocation.get("skill_id") == required_skill_id:
                matched_required_skill = True

        evaluation = _skill_evaluation(call.get("output"))
        if evaluation is None:
            continue
        evidence = evaluation.get("evidence", [])
        evidence_count += len(evidence)
        decision = evaluation.get("decision")
        if isinstance(decision, dict) and decision.get("id"):
            decision_ids.append(str(decision["id"]))

    if required_skill_id and not matched_required_skill:
        reasons.append(f"required Skill was not invoked: {required_skill_id}")
    if skill_calls and not decision_ids:
        reasons.append("no persisted CEPIO Decision identity was found in Skill output")
    if skill_calls and evidence_count < 1:
        reasons.append("Skill output contained no governed evidence references")

    return FoundryG1Qualification(
        passed=not reasons,
        reasons=tuple(reasons),
        tool_names=tool_names,
        skill_evaluation_count=len(skill_calls),
        decision_ids=tuple(decision_ids),
        evidence_count=evidence_count,
    )

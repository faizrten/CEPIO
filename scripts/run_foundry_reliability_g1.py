from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any


G1_ALLOWED_TOOLS = (
    "cepio_get_object",
    "cepio_query_objects",
    "cepio_get_state_at",
    "cepio_explain_property",
    "cepio_call_function",
    "cepio_evaluate_skill",
)

G1_PROHIBITED_TOOLS = (
    "cepio_recommend_action",
    "cepio_execute_action",
)

RELIABILITY_SKILL_ID = "cepio.skill.reliability.investigate-equipment-degradation"


@dataclass(frozen=True)
class Settings:
    project_endpoint: str
    model: str
    mcp_server_url: str
    mcp_connection_name: str
    agent_name: str = "cepio-reliability-g1"
    subject_id: str = "K-101"

    @classmethod
    def from_environment(cls) -> "Settings":
        required = {
            "project_endpoint": "FOUNDRY_PROJECT_ENDPOINT",
            "model": "FOUNDRY_MODEL_DEPLOYMENT_NAME",
            "mcp_server_url": "CEPIO_MCP_SERVER_URL",
            "mcp_connection_name": "CEPIO_MCP_CONNECTION_NAME",
        }
        values: dict[str, str] = {}
        missing: list[str] = []
        for field_name, env_name in required.items():
            value = os.getenv(env_name, "").strip()
            if value:
                values[field_name] = value
            else:
                missing.append(env_name)
        if missing:
            raise RuntimeError("Missing required environment variables: " + ", ".join(missing))

        return cls(
            **values,
            agent_name=os.getenv("CEPIO_FOUNDRY_AGENT_NAME", "cepio-reliability-g1").strip()
            or "cepio-reliability-g1",
            subject_id=os.getenv("CEPIO_G1_SUBJECT_ID", "K-101").strip() or "K-101",
        )


def build_instructions() -> str:
    allowed = ", ".join(G1_ALLOWED_TOOLS)
    return f"""
You are the CEPIO Reliability G1 qualification agent.

You must operate only through the CEPIO MCP tools exposed to you. Do not use general
model knowledge as enterprise truth. Every material claim about the target equipment must
come from CEPIO evidence obtained during this run.

For the requested equipment-degradation investigation:
1. resolve and inspect the subject through CEPIO;
2. retrieve enough governed current/temporal/maintenance evidence to support the assessment;
3. call the governed Skill `{RELIABILITY_SKILL_ID}` through `cepio_evaluate_skill`;
4. treat a BLOCKED or FAILED Skill evaluation as a failed investigation rather than inventing a result;
5. report the resulting CEPIO Decision identity and the CEPIO evidence used;
6. if evidence is insufficient, say so explicitly.

This gate is recommendation/Decision only. No external Action is allowed. The only tool
surface for this qualification is: {allowed}.
""".strip()


def build_prompt(subject_id: str) -> str:
    return (
        f"Investigate degradation of compressor {subject_id}. Produce an evidence-backed "
        "recommendation through CEPIO and report the persisted CEPIO Decision ID. "
        "Do not execute or recommend an external action outside the Skill result."
    )


def _to_plain(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_plain(item) for item in value]
    return value


def _decode_mcp_json(value: Any) -> Any:
    """Decode only structured MCP results, never free-form model narration."""
    if isinstance(value, str):
        try:
            return _decode_mcp_json(json.loads(value))
        except (TypeError, ValueError):
            return None
    if isinstance(value, list):
        if len(value) != 1:
            return None
        item = value[0]
        if not isinstance(item, dict) or item.get("type") != "text":
            return None
        return _decode_mcp_json(item.get("text"))
    if isinstance(value, dict):
        if value.get("isError") is True:
            return None
        if "structuredContent" in value:
            return _decode_mcp_json(value["structuredContent"])
        if "content" in value:
            return _decode_mcp_json(value["content"])
        return value
    return None


def qualify_payload(payload: dict[str, Any]) -> list[str]:
    """Check actual MCP-call results; a textual answer is never proof of a Decision.

    This public check verifies the returned SkillEvaluation structure. The live
    gate additionally needs host-side confirmation that the Decision was
    persisted under the verified actor with traceable, current-run evidence.
    """
    failures: list[str] = []
    if payload.get("status") != "completed":
        failures.append("Foundry response did not complete")

    output = payload.get("output")
    calls = [
        item
        for item in output
        if isinstance(item, dict) and item.get("type") == "mcp_call"
    ] if isinstance(output, list) else []

    for call in calls:
        if call.get("name") in G1_PROHIBITED_TOOLS:
            failures.append(f"G1 response used prohibited tool: {call['name']}")

    skill_calls = [call for call in calls if call.get("name") == "cepio_evaluate_skill"]
    if not skill_calls:
        failures.append("Foundry response does not contain a cepio_evaluate_skill tool call")
        failures.append("Foundry response does not reference the required Reliability Skill")
        return failures

    for call in skill_calls:
        arguments = _decode_mcp_json(call.get("arguments"))
        invocation = arguments.get("invocation", arguments) if isinstance(arguments, dict) else None
        if not isinstance(invocation, dict) or invocation.get("skill_id") != RELIABILITY_SKILL_ID:
            failures.append("Reliability Skill invocation has missing or incorrect skill_id")

        if call.get("error"):
            failures.append("Reliability Skill MCP call returned a tool error")
            continue
        result = _decode_mcp_json(call.get("output"))
        if not isinstance(result, dict):
            failures.append("Reliability Skill MCP output is missing or malformed")
            continue
        if result.get("skill_id") != RELIABILITY_SKILL_ID:
            failures.append("Reliability Skill result has missing or incorrect skill_id")
        if result.get("status") != "completed":
            failures.append("Reliability Skill evaluation did not complete successfully")
        decision = result.get("decision")
        if not isinstance(decision, dict) or not isinstance(decision.get("id"), str) or not decision["id"].strip():
            failures.append("Reliability Skill output lacks a Decision identity")
        evidence = result.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            failures.append("Reliability Skill output lacks structured evidence references")
    return failures


def main() -> int:
    settings = Settings.from_environment()

    try:
        from azure.ai.projects import AIProjectClient
        from azure.ai.projects.models import MCPTool, PromptAgentDefinition
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        raise RuntimeError(
            "Install CEPIO with the 'foundry-agent' extra before running this proof"
        ) from exc

    credential = DefaultAzureCredential()
    project = AIProjectClient(endpoint=settings.project_endpoint, credential=credential)
    openai = project.get_openai_client()

    tool = MCPTool(
        server_label="cepio",
        server_url=settings.mcp_server_url,
        project_connection_id=settings.mcp_connection_name,
        require_approval="never",
        allowed_tools=list(G1_ALLOWED_TOOLS),
    )

    agent = project.agents.create_version(
        agent_name=settings.agent_name,
        definition=PromptAgentDefinition(
            model=settings.model,
            instructions=build_instructions(),
            tools=[tool],
        ),
        description="CEPIO Reliability G1: Foundry-hosted, CEPIO-only, Decision-only proof",
    )

    try:
        response = openai.responses.create(
            input=build_prompt(settings.subject_id),
            extra_body={
                "agent_reference": {"name": agent.name, "type": "agent_reference"},
                "tool_choice": "required",
            },
        )
        payload = _to_plain(response)
        failures = qualify_payload(payload)
        result = {
            "gate": "G1",
            "status": "PASS" if not failures else "FAIL",
            "agent": {"name": agent.name, "version": agent.version},
            "response_id": getattr(response, "id", None),
            "subject_id": settings.subject_id,
            "allowed_tools": list(G1_ALLOWED_TOOLS),
            "prohibited_tools": list(G1_PROHIBITED_TOOLS),
            "failures": failures,
            "output_text": getattr(response, "output_text", None),
            "response": payload,
        }
        print(json.dumps(result, indent=2, sort_keys=True, default=str))
        return 0 if not failures else 1
    finally:
        project.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
        close = getattr(project, "close", None)
        if callable(close):
            close()
        close_credential = getattr(credential, "close", None)
        if callable(close_credential):
            close_credential()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"G1 qualification error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise

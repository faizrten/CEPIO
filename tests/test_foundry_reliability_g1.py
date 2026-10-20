from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_foundry_reliability_g1.py"
SPEC = importlib.util.spec_from_file_location("run_foundry_reliability_g1", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def test_g1_tool_surface_excludes_all_action_tools() -> None:
    assert "cepio_evaluate_skill" in module.G1_ALLOWED_TOOLS
    assert "cepio_recommend_action" not in module.G1_ALLOWED_TOOLS
    assert "cepio_execute_action" not in module.G1_ALLOWED_TOOLS
    assert set(module.G1_ALLOWED_TOOLS).isdisjoint(module.G1_PROHIBITED_TOOLS)


def test_g1_instructions_require_cepio_evidence_and_reliability_skill() -> None:
    instructions = module.build_instructions()
    assert module.RELIABILITY_SKILL_ID in instructions
    assert "enterprise truth" in instructions
    assert "No external Action is allowed" in instructions


def test_g1_prompt_is_subject_specific_and_action_bounded() -> None:
    prompt = module.build_prompt("K-101")
    assert "K-101" in prompt
    assert "persisted CEPIO Decision ID" in prompt
    assert "Do not execute" in prompt


def test_qualifier_accepts_skill_call_without_action_tools() -> None:
    payload = {
        "output": [
            {
                "type": "mcp_call",
                "name": "cepio_evaluate_skill",
                "arguments": {"skill_id": module.RELIABILITY_SKILL_ID},
                "output": {
                    "status": "completed",
                    "skill_id": module.RELIABILITY_SKILL_ID,
                    "decision": {"id": "decision-1"},
                },
            }
        ]
    }
    assert module.qualify_payload(payload) == []


def test_qualifier_fails_without_skill_call() -> None:
    failures = module.qualify_payload({"output": [{"name": "cepio_get_object"}]})
    assert any("cepio_evaluate_skill" in failure for failure in failures)
    assert any("Reliability Skill" in failure for failure in failures)


@pytest.mark.parametrize("tool_name", module.G1_PROHIBITED_TOOLS)
def test_qualifier_fails_when_action_tool_is_used(tool_name: str) -> None:
    payload = {
        "output": [
            {"name": "cepio_evaluate_skill", "skill_id": module.RELIABILITY_SKILL_ID},
            {"name": tool_name},
        ]
    }
    failures = module.qualify_payload(payload)
    assert any(tool_name in failure for failure in failures)


def test_settings_fail_closed_when_required_environment_is_missing(monkeypatch) -> None:
    for name in (
        "FOUNDRY_PROJECT_ENDPOINT",
        "FOUNDRY_MODEL_DEPLOYMENT_NAME",
        "CEPIO_MCP_SERVER_URL",
        "CEPIO_MCP_CONNECTION_NAME",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="Missing required environment variables"):
        module.Settings.from_environment()


def test_settings_read_live_foundry_contract(monkeypatch) -> None:
    values = {
        "FOUNDRY_PROJECT_ENDPOINT": "https://example.services.ai.azure.com/api/projects/cepio",
        "FOUNDRY_MODEL_DEPLOYMENT_NAME": "gpt-example",
        "CEPIO_MCP_SERVER_URL": "https://cepio.example/mcp",
        "CEPIO_MCP_CONNECTION_NAME": "cepio-mcp",
        "CEPIO_FOUNDRY_AGENT_NAME": "reliability-g1",
        "CEPIO_G1_SUBJECT_ID": "K-101",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    settings = module.Settings.from_environment()
    assert settings.project_endpoint == values["FOUNDRY_PROJECT_ENDPOINT"]
    assert settings.mcp_server_url == values["CEPIO_MCP_SERVER_URL"]
    assert settings.agent_name == "reliability-g1"
    assert settings.subject_id == "K-101"

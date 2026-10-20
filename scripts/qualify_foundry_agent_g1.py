from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from cepio.integrations.microsoft.foundry_qualification import qualify_g1_response


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _model_dump(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "to_dict"):
        return value.to_dict()
    raise TypeError(f"Unsupported Foundry response type: {type(value).__name__}")


def main() -> int:
    try:
        from azure.ai.projects import AIProjectClient
        from azure.identity import DefaultAzureCredential
    except ImportError as exc:
        raise RuntimeError(
            "Install CEPIO with the 'foundry-live' extra before running G1 qualification"
        ) from exc

    endpoint = _required_env("CEPIO_FOUNDRY_PROJECT_ENDPOINT")
    agent_name = _required_env("CEPIO_FOUNDRY_AGENT_NAME")
    prompt = _required_env("CEPIO_FOUNDRY_G1_PROMPT")
    required_skill_id = os.getenv("CEPIO_FOUNDRY_G1_SKILL_ID", "").strip() or None
    report_path = Path(
        os.getenv("CEPIO_FOUNDRY_G1_REPORT", "foundry-g1-qualification.json")
    )

    project = AIProjectClient(
        endpoint=endpoint,
        credential=DefaultAzureCredential(),
    )
    openai = project.get_openai_client(agent_name=agent_name)
    response = openai.responses.create(input=prompt)
    payload = _model_dump(response)

    qualification = qualify_g1_response(
        payload,
        required_skill_id=required_skill_id,
    )
    report = {
        "schema_version": "0.1",
        "gate": "G1",
        "agent_name": agent_name,
        "foundry_response_id": payload.get("id"),
        "output_text": getattr(response, "output_text", None),
        "qualification": qualification.to_dict(),
        "response": payload,
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps(report["qualification"], indent=2, sort_keys=True))
    print(f"G1 report: {report_path}")
    return 0 if qualification.passed else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"G1 qualification error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

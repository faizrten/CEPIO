from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any

ENDPOINT = os.environ.get(
    "GITHUB_MODELS_ENDPOINT",
    "https://models.github.ai/inference/chat/completions",
)
MODEL = os.environ.get("GITHUB_MODELS_MODEL", "openai/gpt-5-mini")
MAX_ROUNDS = int(os.environ.get("CEPIO_AGENT_MAX_ROUNDS", "12"))

SYSTEM_PROMPT = """You are an industrial operations agent being evaluated against CEPIO.
You know nothing about the underlying industrial source systems except what CEPIO tools return.
Use ONLY the supplied CEPIO tools for factual industrial claims. Do not guess identifiers, values,
causes, maintenance outcomes, or evidence. Resolve ambiguity with additional CEPIO calls.

When you have enough evidence, return ONLY a JSON object matching the supplied final schema.
The refs array must contain canonical IDs, scenario IDs, event/work-order IDs, canonical IRIs, signal
names, or modality names that directly answer the question. The values array carries scalar answers.
Each factual claim must list the CEPIO tool_call_id values that support it. Those IDs are included in
tool results. Do not cite provider tool-call IDs; cite CEPIO tool_call_id values such as tc-01.
Keep the answer concise and evidence-grounded."""


def _emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _read_line() -> dict[str, Any]:
    line = sys.stdin.readline()
    if not line:
        raise EOFError("CEPIO harness closed the agent protocol")
    return json.loads(line)


def _request(payload: dict[str, Any]) -> dict[str, Any]:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is required for the GitHub Models agent")
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub Models HTTP {exc.code}: {detail}") from exc


def _extract_json(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        raise ValueError(f"Expected model text output, received {type(content).__name__}")
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        if text.lower().startswith("json\n"):
            text = text[5:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise


def _provider_tools(tool_schemas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
            },
        }
        for tool in tool_schemas
    ]


def main() -> int:
    challenge = _read_line()
    if challenge.get("type") != "challenge":
        raise ValueError("First protocol message must be a CEPIO challenge")

    question = str(challenge["question"])
    tools = _provider_tools(challenge.get("tools", []))
    final_schema = challenge.get("final_schema", {})
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Industrial question: {question}\n\n"
                "Use CEPIO tools as needed. Your final response must be only JSON matching this schema:\n"
                + json.dumps(final_schema, separators=(",", ":"))
            ),
        },
    ]

    for _round in range(MAX_ROUNDS):
        response = _request(
            {
                "model": MODEL,
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto",
            }
        )
        choices = response.get("choices") or []
        if not choices:
            raise RuntimeError(f"GitHub Models returned no choices: {response}")
        message = choices[0].get("message") or {}
        tool_calls = message.get("tool_calls") or []

        if tool_calls:
            assistant_message: dict[str, Any] = {
                "role": "assistant",
                "content": message.get("content"),
                "tool_calls": tool_calls,
            }
            messages.append(assistant_message)
            for provider_call in tool_calls:
                function = provider_call.get("function") or {}
                name = str(function.get("name", ""))
                raw_arguments = function.get("arguments") or "{}"
                arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
                request_id = str(provider_call.get("id") or f"model-call-{_round}")
                _emit(
                    {
                        "type": "tool_call",
                        "id": request_id,
                        "name": name,
                        "arguments": arguments,
                    }
                )
                tool_result = _read_line()
                if tool_result.get("type") != "tool_result":
                    raise ValueError(f"Expected tool_result, received: {tool_result}")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": request_id,
                        "content": json.dumps(
                            {
                                "cepio_tool_call_id": tool_result.get("tool_call_id"),
                                "result": tool_result.get("result"),
                            },
                            separators=(",", ":"),
                        ),
                    }
                )
            continue

        final = _extract_json(message.get("content", ""))
        _emit({"type": "final", "answer": final})
        return 0

    raise RuntimeError(f"Model exceeded {MAX_ROUNDS} tool-use rounds without a final answer")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"github_models_agent error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise

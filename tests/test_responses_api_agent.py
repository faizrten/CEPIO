from __future__ import annotations

import asyncio
import importlib.util
import json
import queue
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class _QueuedStdin:
    def __init__(self) -> None:
        self.responses: queue.Queue[str | None] = queue.Queue()

    def readline(self) -> str:
        value = self.responses.get(timeout=5)
        return "" if value is None else value + "\n"


def _load_agent():
    path = ROOT / "scripts/responses_api_agent.py"
    spec = importlib.util.spec_from_file_location("responses_api_agent_test", path)
    assert spec is not None and spec.loader is not None
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)
    return agent


def test_response_tool_preserves_cepio_schema():
    agent = _load_agent()
    schema = {
        "name": "search_objects",
        "description": "Search CEPIO objects",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    }
    assert agent._response_tool(schema) == {"type": "function", **schema}


def test_parallel_function_calls_preserve_cepio_evidence_ids(monkeypatch):
    agent = _load_agent()

    class Router:
        async def call(self, name, arguments):
            await asyncio.sleep(0 if name == "get_events" else 0.01)
            return {"tool_call_id": f"tc-{arguments['n']}", "result": {"name": name}}

    calls = [
        types.SimpleNamespace(
            type="function_call",
            name="search_objects",
            arguments='{"n":1}',
            call_id="fc-1",
        ),
        types.SimpleNamespace(
            type="function_call",
            name="get_events",
            arguments='{"n":2}',
            call_id="fc-2",
        ),
    ]

    outputs = asyncio.run(agent._execute_function_calls(calls, Router()))
    assert [item["call_id"] for item in outputs] == ["fc-1", "fc-2"]
    decoded = [json.loads(item["output"]) for item in outputs]
    assert decoded == [
        {"cepio_tool_call_id": "tc-1", "result": {"name": "search_objects"}},
        {"cepio_tool_call_id": "tc-2", "result": {"name": "get_events"}},
    ]


def test_full_stateless_responses_loop_routes_parallel_tools(monkeypatch):
    agent = _load_agent()
    stdin = _QueuedStdin()
    challenge = {
        "type": "challenge",
        "question": "Which asset should be investigated?",
        "tools": [
            {"name": "search_objects", "description": "search", "parameters": {"type": "object"}},
            {"name": "get_events", "description": "events", "parameters": {"type": "object"}},
        ],
        "final_schema": {"answer": "string", "refs": ["string"]},
    }
    stdin.responses.put(json.dumps(challenge))
    monkeypatch.setattr(agent.sys, "stdin", stdin)

    emitted = []

    def emit(payload):
        emitted.append(payload)
        if payload.get("type") == "tool_call":
            n = 1 if payload["name"] == "search_objects" else 2
            stdin.responses.put(
                json.dumps(
                    {
                        "type": "tool_result",
                        "request_id": payload["id"],
                        "tool_call_id": f"tc-{n}",
                        "result": {"n": n},
                    }
                )
            )

    monkeypatch.setattr(agent, "_emit", emit)

    first_output = [
        types.SimpleNamespace(type="reasoning", id="r-1"),
        types.SimpleNamespace(
            type="function_call",
            name="search_objects",
            arguments='{"query":"Rig-07"}',
            call_id="fc-1",
        ),
        types.SimpleNamespace(
            type="function_call",
            name="get_events",
            arguments='{"object_id":"rig-07"}',
            call_id="fc-2",
        ),
    ]
    first = types.SimpleNamespace(output=first_output, output_text="")
    final_text = json.dumps(
        {
            "answer": "Investigate the asset.",
            "refs": ["asset-1"],
            "values": [],
            "claims": [{"text": "Supported", "supported_by": ["tc-1", "tc-2"]}],
            "confidence": 0.9,
        }
    )
    second = types.SimpleNamespace(output=[], output_text=final_text)

    class Responses:
        def __init__(self):
            self.calls = []

        async def create(self, **kwargs):
            self.calls.append(kwargs)
            return first if len(self.calls) == 1 else second

    class Client:
        def __init__(self):
            self.responses = Responses()
            self.closed = False

        async def close(self):
            self.closed = True

    client = Client()
    monkeypatch.setattr(agent, "_create_client", lambda: client)

    try:
        assert asyncio.run(agent._run()) == 0
    finally:
        stdin.responses.put(None)

    assert len(client.responses.calls) == 2
    assert all(call["store"] is False for call in client.responses.calls)
    assert all(call["instructions"] == agent.SYSTEM_PROMPT for call in client.responses.calls)
    assert client.responses.calls[0]["model"] == agent.MODEL

    second_inputs = client.responses.calls[1]["input"]
    outputs = [
        item
        for item in second_inputs
        if isinstance(item, dict) and item.get("type") == "function_call_output"
    ]
    assert [item["call_id"] for item in outputs] == ["fc-1", "fc-2"]
    assert [json.loads(item["output"])["cepio_tool_call_id"] for item in outputs] == [
        "tc-1",
        "tc-2",
    ]
    assert emitted[-1]["type"] == "final"
    assert emitted[-1]["answer"]["claims"][0]["supported_by"] == ["tc-1", "tc-2"]
    assert client.closed is True


def test_client_config_accepts_azure_aliases(monkeypatch):
    agent = _load_agent()
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AZURE_OPENAI_BASE_URL", "https://example.openai.azure.com/openai/v1")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "secret")
    assert agent._client_config() == (
        "https://example.openai.azure.com/openai/v1/",
        "secret",
    )

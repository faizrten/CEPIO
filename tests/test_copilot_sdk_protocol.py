from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import queue
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class _Tool:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _ToolResult:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _QueuedStdin:
    def __init__(self):
        self.responses: queue.Queue[str] = queue.Queue()

    def readline(self) -> str:
        return self.responses.get(timeout=5) + "\n"


def _load_agent(monkeypatch):
    copilot = types.ModuleType("copilot")
    copilot.CopilotClient = object
    mode = types.ModuleType("copilot._mode")
    mode.ToolSet = object
    session = types.ModuleType("copilot.session")
    session.PermissionHandler = object
    tools = types.ModuleType("copilot.tools")
    tools.Tool = _Tool
    tools.ToolInvocation = object
    tools.ToolResult = _ToolResult
    for name, module in (
        ("copilot", copilot),
        ("copilot._mode", mode),
        ("copilot.session", session),
        ("copilot.tools", tools),
    ):
        monkeypatch.setitem(sys.modules, name, module)

    path = ROOT / "scripts/copilot_sdk_agent.py"
    spec = importlib.util.spec_from_file_location("copilot_sdk_agent_test", path)
    assert spec is not None and spec.loader is not None
    agent = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(agent)
    return agent


def test_concurrent_tool_handlers_exchange_correlated_protocol_messages(monkeypatch):
    agent = _load_agent(monkeypatch)
    stdin = _QueuedStdin()
    monkeypatch.setattr(agent.sys, "stdin", stdin)
    stdout = io.StringIO()
    monkeypatch.setattr(agent.sys, "stdout", stdout)

    async def exercise_handlers():
        async def wait_for_line_count(count: int) -> None:
            async def wait() -> None:
                while len(stdout.getvalue().splitlines()) < count:
                    await asyncio.sleep(0)

            await asyncio.wait_for(wait(), timeout=2)

        lock = asyncio.Lock()
        first = agent._make_tool({"name": "first"}, lock)
        second = agent._make_tool({"name": "second"}, lock)
        first_task = asyncio.create_task(first.handler(types.SimpleNamespace(arguments={})))
        second_task = asyncio.create_task(second.handler(types.SimpleNamespace(arguments={})))

        await wait_for_line_count(1)
        first_request = json.loads(stdout.getvalue().splitlines()[0])
        assert len(stdout.getvalue().splitlines()) == 1
        stdin.responses.put(
            json.dumps(
                {
                    "type": "tool_result",
                    "request_id": first_request["id"],
                    "tool_call_id": "tc-01",
                    "result": {"value": 1},
                }
            )
        )

        await wait_for_line_count(2)
        second_request = json.loads(stdout.getvalue().splitlines()[1])
        stdin.responses.put(
            json.dumps(
                {
                    "type": "tool_result",
                    "request_id": second_request["id"],
                    "tool_call_id": "tc-02",
                    "result": {"value": 2},
                }
            )
        )
        return await asyncio.gather(first_task, second_task)

    results = asyncio.run(exercise_handlers())
    assert [json.loads(result.text_result_for_llm)["cepio_tool_call_id"] for result in results] == [
        "tc-01",
        "tc-02",
    ]

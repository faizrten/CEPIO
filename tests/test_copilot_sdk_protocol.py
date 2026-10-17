from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import queue
import sys
import types
import subprocess
import threading

import pytest
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


def test_parallel_results_are_routed_out_of_order(monkeypatch):
    agent = _load_agent(monkeypatch)
    stdin = _QueuedStdin()
    monkeypatch.setattr(agent.sys, "stdin", stdin)
    stdout = io.StringIO()
    monkeypatch.setattr(agent.sys, "stdout", stdout)

    async def exercise():
        router = agent.ProtocolRouter()
        try:
            tools = [agent._make_tool({"name": "same"}, router) for _ in range(3)]
            tasks = [asyncio.create_task(tool.handler(types.SimpleNamespace(arguments={"i": i})))
                     for i, tool in enumerate(tools)]
            async def emitted():
                while len(stdout.getvalue().splitlines()) < 3:
                    await asyncio.sleep(0)
            await asyncio.wait_for(emitted(), 2)
            requests = [json.loads(line) for line in stdout.getvalue().splitlines()]
            assert len({r["id"] for r in requests}) == 3
            for request in reversed(requests):
                i = request["arguments"]["i"]
                stdin.responses.put(json.dumps({"type": "tool_result", "request_id": request["id"],
                    "tool_call_id": f"tc-{i}", "result": {"value": i}}))
            results = await asyncio.wait_for(asyncio.gather(*tasks), 2)
            assert [json.loads(r.text_result_for_llm) for r in results] == [
                {"cepio_tool_call_id": f"tc-{i}", "result": {"value": i}} for i in range(3)]
            assert not router.pending
        finally:
            router.close()
            stdin.responses.put("")
            await asyncio.to_thread(router.reader.join, 2)
            assert not router.reader.is_alive()
    asyncio.run(exercise())


@pytest.mark.parametrize("response", ["", '{"type":"tool_result","request_id":"unknown"}'])
def test_eof_or_bad_correlation_fails_all_pending_calls(monkeypatch, response):
    agent = _load_agent(monkeypatch)
    stdin = _QueuedStdin()
    monkeypatch.setattr(agent.sys, "stdin", stdin)
    monkeypatch.setattr(agent, "_emit", lambda payload: None)
    async def exercise():
        router = agent.ProtocolRouter()
        tasks = [asyncio.create_task(router.call("test", {})) for _ in range(2)]
        await asyncio.sleep(0)
        stdin.responses.put(response)
        results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), 2)
        assert all(isinstance(r, (ValueError, EOFError)) for r in results)
        assert not router.pending
        router.close()
        stdin.responses.put("")
        await asyncio.to_thread(router.reader.join, 2)
    asyncio.run(exercise())


def test_child_exits_with_parent_stdin_still_open(tmp_path):
    child = tmp_path / "router_child.py"
    child.write_text(f"""
import runpy, asyncio, types, json
import pytest
ns = runpy.run_path({str(Path(__file__).resolve())!r})
patch = pytest.MonkeyPatch()
agent = ns['_load_agent'](patch)
async def run():
    router = agent.ProtocolRouter()
    try:
        tools = [agent._make_tool({{'name':'test'}}, router) for _ in range(3)]
        results = await asyncio.gather(*(t.handler(types.SimpleNamespace(arguments={{'i':i}})) for i,t in enumerate(tools)))
        agent._emit({{'type':'final','answer':{{'results':[json.loads(r.text_result_for_llm) for r in results]}}}})
    finally:
        router.close()
asyncio.run(run())
""")
    proc = subprocess.Popen([sys.executable, str(child)], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    lines = queue.Queue()
    def read_lines():
        for line in proc.stdout:
            lines.put(line)
    reader = threading.Thread(target=read_lines, daemon=True)
    reader.start()
    try:
        requests = [json.loads(lines.get(timeout=5)) for _ in range(3)]
        for request in reversed(requests):
            i = request['arguments']['i']
            proc.stdin.write(json.dumps({'type':'tool_result', 'request_id':request['id'],
                                        'tool_call_id':f'tc-{i}', 'result':i}) + "\n")
        proc.stdin.flush()
        final = json.loads(lines.get(timeout=5))
        assert final['answer']['results'] == [
            {'cepio_tool_call_id':f'tc-{i}', 'result':i} for i in range(3)]
        assert proc.wait(timeout=5) == 0
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)
        reader.join(timeout=2)
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            stream.close()


@pytest.mark.parametrize("mode", ["burst", "timeout", "eof"])
def test_harness_drains_bursts_and_reaps_child(monkeypatch, tmp_path, mode):
    ns = __import__('runpy').run_path(str(ROOT / 'tests/test_agent_challenge.py'))
    module = ns['_load_module']()
    child = tmp_path / 'burst.py'
    child.write_text(r"""
import sys, json, time
json.loads(sys.stdin.readline())
mode = sys.argv[1]
if mode == 'timeout':
    time.sleep(30)
elif mode == 'burst':
    sys.stderr.write('diagnostic\n' * 20000)
    sys.stderr.flush()
    sys.stdout.write(''.join(json.dumps({'type':'tool_call','id':str(i),'name':'test','arguments':{'i':i}})+'\n' for i in range(3)))
    sys.stdout.flush()
    results = [json.loads(sys.stdin.readline()) for _ in range(3)]
    print(json.dumps({'type':'final','answer':{'results':results}}), flush=True)
""")
    created = []
    original = module.base.subprocess.Popen
    def capture(*args, **kwargs):
        proc = original(*args, **kwargs)
        created.append(proc)
        return proc
    monkeypatch.setattr(module.base.subprocess, 'Popen', capture)
    class Gateway:
        tool_schemas = []
        def call(self, name, arguments):
            i = arguments['i']
            return f'tc-{i}', i
    command = f'"{sys.executable}" "{child}" {mode}'
    adapter = module.StrictExternalProcessAgent(command, timeout_seconds=1 if mode == 'timeout' else 10)
    if mode == 'burst':
        answer = adapter.run('synthetic transport test', Gateway())
        assert [(r['request_id'], r['tool_call_id'], r['result']) for r in answer['results']] == [
            (str(i), f'tc-{i}', i) for i in range(3)]
    else:
        with pytest.raises(TimeoutError if mode == 'timeout' else RuntimeError):
            adapter.run('synthetic transport test', Gateway())
    assert created[0].poll() is not None
    assert all(s.closed for s in (created[0].stdin, created[0].stdout, created[0].stderr))

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import threading
from itertools import count
from typing import Any

from copilot import CopilotClient
from copilot._mode import ToolSet
from copilot.session import PermissionHandler
from copilot.tools import Tool, ToolInvocation, ToolResult

MODEL = os.environ.get("COPILOT_MODEL", "gpt-5.4")

SYSTEM_PROMPT = """You are the model under evaluation in CEPIO Agent Challenge v0.1.
You have no direct access to industrial source systems, repository files, shell, databases, or the hidden evaluator.
Use only the custom CEPIO tools supplied to this session for factual industrial claims.
Do not guess identifiers, values, causes, maintenance outcomes, asset identity, or evidence.
Resolve ambiguity by making additional CEPIO tool calls.

Your final answer MUST be only a JSON object with keys:
- answer: concise human-readable conclusion
- refs: list of canonical IDs, scenario IDs, event/work-order IDs, canonical IRIs, signal names, or modality names that directly answer the question
- values: list of scalar values that directly answer the question
- claims: list of {text, supported_by} where supported_by contains CEPIO tool-call IDs such as tc-01
- confidence: number from 0 to 1

Each CEPIO tool result contains a cepio_tool_call_id. Cite those IDs in supported_by. Never invent tool-call IDs."""


def _emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def _read_protocol_line() -> dict[str, Any]:
    line = sys.stdin.readline()
    if not line:
        raise EOFError("CEPIO challenge harness closed the protocol")
    return json.loads(line)


class ProtocolRouter:
    """One daemon reader routes stdin results to event-loop-owned futures.

    A daemon is intentional: stdin may remain open after the final answer, and
    asyncio's default executor would otherwise wait forever during shutdown.
    """

    def __init__(self) -> None:
        self.loop = asyncio.get_running_loop()
        self.pending: dict[str, asyncio.Future] = {}
        self.sequence = count(1)
        self.closed = False
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self) -> None:
        while not self.closed:
            try:
                response = _read_protocol_line()
            except Exception as exc:
                self._schedule(self.close, exc)
                return
            self._schedule(self._dispatch, response)

    def _schedule(self, callback, value) -> None:
        try:
            self.loop.call_soon_threadsafe(callback, value)
        except RuntimeError:
            pass  # Event loop already closed after final answer.

    def _dispatch(self, response: dict[str, Any]) -> None:
        if self.closed:
            return
        request_id = response.get("request_id") if isinstance(response, dict) else None
        if (not isinstance(request_id, str) or response.get("type") != "tool_result"
                or request_id not in self.pending):
            self.close(ValueError(f"Unexpected protocol response: {response}"))
            return
        future = self.pending.pop(request_id)
        if not future.done():
            future.set_result(response)

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.closed:
            raise EOFError("CEPIO protocol router is closed")
        request_id = f"copilot-{next(self.sequence)}"
        future = self.loop.create_future()
        self.pending[request_id] = future
        try:
            _emit({"type": "tool_call", "id": request_id, "name": name, "arguments": arguments})
            return await future
        finally:
            self.pending.pop(request_id, None)

    def close(self, error: Exception | None = None) -> None:
        self.closed = True
        for future in self.pending.values():
            if not future.done():
                future.set_exception(error or EOFError("CEPIO protocol router closed"))
        self.pending.clear()


def _extract_json(content: Any) -> dict[str, Any]:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        raise ValueError(f"Expected final text, got {type(content).__name__}")
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


def _make_tool(schema: dict[str, Any], router: ProtocolRouter) -> Tool:
    name = str(schema["name"])

    async def handler(invocation: ToolInvocation) -> ToolResult:
        response = await router.call(name, dict(invocation.arguments or {}))
        payload = {"cepio_tool_call_id": response.get("tool_call_id"), "result": response.get("result")}
        return ToolResult(
            text_result_for_llm=json.dumps(payload, separators=(",", ":")),
            result_type="success",
            session_log=f"CEPIO {name} -> {response.get('tool_call_id')}",
        )

    return Tool(
        name=name,
        description=str(schema.get("description", "")),
        parameters=schema.get("parameters") or {"type": "object", "properties": {}},
        handler=handler,
        defer="never",
    )


def _event_name(event: Any) -> str:
    value = getattr(event, "type", "unknown")
    return str(getattr(value, "value", value))


async def _run() -> int:
    challenge = _read_protocol_line()
    if challenge.get("type") != "challenge":
        raise ValueError("First protocol message must be a CEPIO challenge")

    question = str(challenge["question"])
    router = ProtocolRouter()
    tools = [_make_tool(schema, router) for schema in (challenge.get("tools") or [])]
    available_tools = ToolSet()
    for tool in tools:
        available_tools.add_custom(tool.name)
    final_schema = challenge.get("final_schema") or {}
    prompt = (
        f"Industrial question: {question}\n\n"
        "Use the CEPIO tools as needed. Return only JSON matching this final schema:\n"
        + json.dumps(final_schema, separators=(",", ":"))
    )

    try:
        token = os.environ.get("GITHUB_TOKEN")
        with tempfile.TemporaryDirectory(prefix="cepio-copilot-empty-") as base_directory:
            async with CopilotClient(mode="empty", base_directory=base_directory, github_token=token) as client:
                models = await asyncio.wait_for(client.list_models(), timeout=20.0)
                model_ids = [str(getattr(model, "id", "")) for model in models]
                print(
                    f"CEPIO Copilot child preflight: configured={MODEL} available={MODEL in model_ids} models={','.join(model_ids)}",
                    file=sys.stderr,
                    flush=True,
                )
                if MODEL not in model_ids:
                    raise RuntimeError(f"Configured Copilot model is unavailable: {MODEL}")
                async with await client.create_session(
                    model=MODEL,
                    tools=tools,
                    available_tools=available_tools,
                    on_permission_request=PermissionHandler.approve_all,
                    system_message={"mode": "append", "content": SYSTEM_PROMPT},
                    infinite_sessions={"enabled": False},
                ) as session:
                    def on_event(event: Any) -> None:
                        name = _event_name(event)
                        if name in {"session.start", "session.idle", "session.error", "assistant.message", "tool.execution_start", "tool.execution_complete"}:
                            if name == "session.error":
                                data = getattr(event, "data", None)
                                print(
                                    "CEPIO Copilot event: session.error "
                                    f"type={getattr(data, 'error_type', None)} "
                                    f"status={getattr(data, 'status_code', None)} "
                                    f"message={getattr(data, 'message', None)}",
                                    file=sys.stderr,
                                    flush=True,
                                )
                            else:
                                print(f"CEPIO Copilot event: {name}", file=sys.stderr, flush=True)

                    session.on(on_event)
                    print("CEPIO Copilot: session created; sending challenge prompt", file=sys.stderr, flush=True)
                    response = await session.send_and_wait(prompt, timeout=90.0)
                    if response is None:
                        raise RuntimeError("Copilot session completed without an assistant message")
                    content = getattr(getattr(response, "data", None), "content", None)
                    if content is None:
                        raise RuntimeError(f"Copilot response had no content: {response!r}")
                    final = _extract_json(content)
                    _emit({"type": "final", "answer": final})
                    return 0
    finally:
        router.close()


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"copilot_sdk_agent error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
        raise

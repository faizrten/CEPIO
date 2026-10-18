from __future__ import annotations

import asyncio
import json
import os
import sys
import threading
from itertools import count
from typing import Any

MODEL = os.environ.get("CEPIO_MODEL", "gpt-6-astra")
PROVIDER = os.environ.get("CEPIO_MODEL_PROVIDER", "azure-foundry-responses")
MAX_TURNS = int(os.environ.get("CEPIO_AGENT_MAX_TURNS", "20"))

# Keep this prompt byte-for-byte aligned with the existing Copilot adapter so
# provider comparisons change the model/provider, not the benchmark contract.
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
    """Route concurrent CEPIO tool results back to Responses API calls by request ID."""

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
            pass

    def _dispatch(self, response: dict[str, Any]) -> None:
        if self.closed:
            return
        request_id = response.get("request_id") if isinstance(response, dict) else None
        if (
            not isinstance(request_id, str)
            or response.get("type") != "tool_result"
            or request_id not in self.pending
        ):
            self.close(ValueError(f"Unexpected protocol response: {response}"))
            return
        future = self.pending.pop(request_id)
        if not future.done():
            future.set_result(response)

    async def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.closed:
            raise EOFError("CEPIO protocol router is closed")
        request_id = f"responses-{next(self.sequence)}"
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


def _response_tool(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "function",
        "name": str(schema["name"]),
        "description": str(schema.get("description", "")),
        "parameters": schema.get("parameters") or {"type": "object", "properties": {}},
    }


def _client_config() -> tuple[str, str]:
    base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get("AZURE_OPENAI_BASE_URL")
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AZURE_OPENAI_API_KEY")
    if not base_url:
        raise RuntimeError(
            "OPENAI_BASE_URL or AZURE_OPENAI_BASE_URL is required; for Azure use "
            "https://<resource>.openai.azure.com/openai/v1/"
        )
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY or AZURE_OPENAI_API_KEY is required")
    return base_url.rstrip("/") + "/", api_key


def _create_client():
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:
        raise RuntimeError(
            "openai package is required: python -m pip install 'openai>=2,<3'"
        ) from exc
    base_url, api_key = _client_config()
    return AsyncOpenAI(base_url=base_url, api_key=api_key)


def _function_calls(response: Any) -> list[Any]:
    return [
        item
        for item in (getattr(response, "output", None) or [])
        if getattr(item, "type", None) == "function_call"
    ]


async def _execute_function_calls(calls: list[Any], router: ProtocolRouter) -> list[dict[str, Any]]:
    async def execute(item: Any) -> dict[str, Any]:
        name = str(getattr(item, "name"))
        raw_arguments = getattr(item, "arguments", "{}") or "{}"
        arguments = (
            json.loads(raw_arguments) if isinstance(raw_arguments, str) else dict(raw_arguments)
        )
        response = await router.call(name, arguments)
        payload = {
            "cepio_tool_call_id": response.get("tool_call_id"),
            "result": response.get("result"),
        }
        return {
            "type": "function_call_output",
            "call_id": str(getattr(item, "call_id")),
            "output": json.dumps(payload, separators=(",", ":")),
        }

    return list(await asyncio.gather(*(execute(item) for item in calls)))


async def _run() -> int:
    challenge = _read_protocol_line()
    if challenge.get("type") != "challenge":
        raise ValueError("First protocol message must be a CEPIO challenge")

    question = str(challenge["question"])
    tools = [_response_tool(schema) for schema in (challenge.get("tools") or [])]
    final_schema = challenge.get("final_schema") or {}
    prompt = (
        f"Industrial question: {question}\n\n"
        "Use the CEPIO tools as needed. Return only JSON matching this final schema:\n"
        + json.dumps(final_schema, separators=(",", ":"))
    )

    router = ProtocolRouter()
    client = _create_client()
    inputs: list[Any] = [{"role": "user", "content": prompt}]
    try:
        print(
            f"CEPIO Responses agent: provider={PROVIDER} model={MODEL} stateless=True",
            file=sys.stderr,
            flush=True,
        )
        for turn in range(1, MAX_TURNS + 1):
            response = await client.responses.create(
                model=MODEL,
                instructions=SYSTEM_PROMPT,
                input=inputs,
                tools=tools,
                store=False,
            )
            calls = _function_calls(response)
            print(
                f"CEPIO Responses agent: turn={turn} function_calls={len(calls)}",
                file=sys.stderr,
                flush=True,
            )
            if not calls:
                content = getattr(response, "output_text", None)
                if not content:
                    raise RuntimeError(f"Responses API returned no final text: {response!r}")
                final = _extract_json(content)
                _emit({"type": "final", "answer": final})
                return 0

            # Stateless Responses chaining: preserve every model output item, including
            # reasoning items, then append CEPIO function outputs before the next turn.
            inputs.extend(getattr(response, "output", None) or [])
            inputs.extend(await _execute_function_calls(calls, router))

        raise TimeoutError(f"Responses agent exceeded {MAX_TURNS} model turns")
    finally:
        router.close()
        close = getattr(client, "close", None)
        if close is not None:
            result = close()
            if asyncio.iscoroutine(result):
                await result


def main() -> int:
    return asyncio.run(_run())


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(
            f"responses_api_agent error: {type(exc).__name__}: {exc}", file=sys.stderr, flush=True
        )
        raise

"""Constrained CEPIO Operator Agent.

The Operator is intentionally separated from :class:`CEPIORuntime`. It can discover
enterprise facts only through a governed tool gateway (MCP or REST). A planner may be
LLM-backed, scripted, or otherwise agentic, but planner output is never itself accepted
as enterprise evidence.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable, Literal, Protocol
from urllib import parse, request

from pydantic import BaseModel, Field


OperatorStatus = Literal[
    "ANSWERED",
    "INSUFFICIENT_CEPIO_EVIDENCE",
    "REJECTED_UNSUPPORTED_EVIDENCE",
]


class ToolRequest(BaseModel):
    kind: Literal["tool"] = "tool"
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class FinalResponse(BaseModel):
    kind: Literal["final"] = "final"
    status: OperatorStatus
    answer: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


OperatorPlanStep = ToolRequest | FinalResponse


class ToolEvidence(BaseModel):
    id: str
    tool_name: str
    arguments: dict[str, Any]
    payload: dict[str, Any]


class OperatorTraceEntry(BaseModel):
    step: int
    request: ToolRequest
    evidence: ToolEvidence | None = None
    error: str | None = None


class OperatorResult(BaseModel):
    question_id: str
    status: OperatorStatus
    answer: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    evidence: list[ToolEvidence] = Field(default_factory=list)
    tool_trace: list[OperatorTraceEntry] = Field(default_factory=list)


class OperatorToolGateway(Protocol):
    """The only enterprise-fact boundary available to the Operator."""

    def list_tools(self) -> list[dict[str, Any]]: ...

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


class OperatorPlanner(Protocol):
    """Reasoning component. It may propose tool calls or a final structured answer."""

    def next_step(
        self,
        *,
        question_id: str,
        question: str,
        tools: list[dict[str, Any]],
        trace: list[OperatorTraceEntry],
    ) -> OperatorPlanStep: ...


class MCPToolGateway:
    """Adapter for CEPIO's existing MCP facade without exposing the runtime to the agent."""

    def __init__(self, facade: Any) -> None:
        self._facade = facade

    def list_tools(self) -> list[dict[str, Any]]:
        return self._facade.list_tools()

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        value = self._facade.call_tool(name, arguments)
        if not isinstance(value, dict):
            return {"result": value}
        return value


@dataclass(frozen=True)
class RestGatewaySettings:
    base_url: str
    bearer_token: str | None = None
    timeout_seconds: float = 10.0


class RESTToolGateway:
    """Small CEPIO REST adapter using only the public API surface.

    It intentionally mirrors the MCP tool vocabulary so an Operator planner can switch
    transport without gaining additional enterprise-truth access.
    """

    def __init__(
        self,
        settings: RestGatewaySettings,
        *,
        transport: Callable[[str, str, dict[str, Any] | None, dict[str, str]], Any] | None = None,
    ) -> None:
        self.settings = settings
        self._transport = transport or self._http_transport

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "cepio_get_object",
                "description": "Read an authorized CEPIO object by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {"object_id": {"type": "string"}},
                    "required": ["object_id"],
                },
            },
            {
                "name": "cepio_neighbors",
                "description": "Traverse outgoing CEPIO relationships",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "object_id": {"type": "string"},
                        "relationship_type": {"type": ["string", "null"]},
                    },
                    "required": ["object_id"],
                },
            },
            {
                "name": "cepio_call_function",
                "description": "Invoke a registered CEPIO business function",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "function": {"type": "string"},
                        "arguments": {"type": "object"},
                    },
                    "required": ["function", "arguments"],
                },
            },
            {
                "name": "cepio_execute_action",
                "description": "Attempt a governed CEPIO action",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action_type": {"type": "string"},
                        "target_id": {"type": "string"},
                        "target_type": {"type": "string"},
                        "parameters": {"type": "object"},
                        "idempotency_key": {"type": ["string", "null"]},
                    },
                    "required": ["action_type", "target_id", "target_type"],
                },
            },
        ]

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        headers = {"Accept": "application/json"}
        if self.settings.bearer_token:
            headers["Authorization"] = f"Bearer {self.settings.bearer_token}"

        if name == "cepio_get_object":
            object_id = parse.quote(str(arguments["object_id"]), safe="")
            value = self._transport("GET", f"/objects/{object_id}", None, headers)
            return value if isinstance(value, dict) else {"result": value}

        if name == "cepio_neighbors":
            object_id = parse.quote(str(arguments["object_id"]), safe="")
            relationship_type = arguments.get("relationship_type")
            path = f"/objects/{object_id}/neighbors"
            if relationship_type:
                path += "?" + parse.urlencode({"relationship_type": relationship_type})
            value = self._transport("GET", path, None, headers)
            if isinstance(value, list):
                return {"objects": value}
            return value if isinstance(value, dict) else {"result": value}

        if name == "cepio_call_function":
            function_name = parse.quote(str(arguments["function"]), safe="")
            value = self._transport(
                "POST",
                f"/functions/{function_name}",
                {"arguments": arguments.get("arguments", {})},
                headers,
            )
            return value if isinstance(value, dict) else {"result": value}

        if name == "cepio_execute_action":
            value = self._transport(
                "POST",
                "/actions",
                {
                    "action_type": arguments["action_type"],
                    "target": {"id": arguments["target_id"], "type": arguments["target_type"]},
                    "parameters": arguments.get("parameters", {}),
                    "idempotency_key": arguments.get("idempotency_key"),
                },
                headers,
            )
            return value if isinstance(value, dict) else {"result": value}

        raise KeyError(f"Unknown CEPIO REST Operator tool: {name}")

    def _http_transport(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None,
        headers: dict[str, str],
    ) -> Any:
        url = self.settings.base_url.rstrip("/") + path
        data = None
        request_headers = dict(headers)
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        req = request.Request(url, data=data, headers=request_headers, method=method)
        with request.urlopen(req, timeout=self.settings.timeout_seconds) as response:  # nosec B310 - URL is explicit CEPIO endpoint
            return json.loads(response.read().decode("utf-8"))


def _stable_evidence_id(tool_name: str, arguments: dict[str, Any], payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"tool": tool_name, "arguments": arguments, "payload": payload},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return "cepio-tool-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


class ConstrainedOperatorAgent:
    """Tool-using Operator whose enterprise assertions must cite CEPIO tool evidence."""

    def __init__(
        self,
        *,
        gateway: OperatorToolGateway,
        planner: OperatorPlanner,
        max_tool_steps: int = 12,
    ) -> None:
        if max_tool_steps < 1:
            raise ValueError("max_tool_steps must be positive")
        self.gateway = gateway
        self.planner = planner
        self.max_tool_steps = max_tool_steps

    def run(self, *, question_id: str, question: str) -> OperatorResult:
        tools = self.gateway.list_tools()
        allowed_tools = {str(tool.get("name")) for tool in tools if tool.get("name")}
        trace: list[OperatorTraceEntry] = []
        evidence: list[ToolEvidence] = []

        for step_number in range(1, self.max_tool_steps + 2):
            step = self.planner.next_step(
                question_id=question_id,
                question=question,
                tools=tools,
                trace=list(trace),
            )

            if isinstance(step, FinalResponse):
                return self._finalize(question_id, step, trace, evidence)

            if step_number > self.max_tool_steps:
                return OperatorResult(
                    question_id=question_id,
                    status="INSUFFICIENT_CEPIO_EVIDENCE",
                    answer=None,
                    evidence=[*evidence],
                    tool_trace=trace,
                )

            if step.name not in allowed_tools:
                trace.append(
                    OperatorTraceEntry(
                        step=step_number,
                        request=step,
                        error=f"Tool is not exposed by CEPIO gateway: {step.name}",
                    )
                )
                continue

            try:
                payload = self.gateway.call_tool(step.name, step.arguments)
                item = ToolEvidence(
                    id=_stable_evidence_id(step.name, step.arguments, payload),
                    tool_name=step.name,
                    arguments=step.arguments,
                    payload=payload,
                )
                evidence.append(item)
                trace.append(OperatorTraceEntry(step=step_number, request=step, evidence=item))
            except Exception as exc:
                trace.append(
                    OperatorTraceEntry(
                        step=step_number,
                        request=step,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )

        return OperatorResult(
            question_id=question_id,
            status="INSUFFICIENT_CEPIO_EVIDENCE",
            answer=None,
            evidence=evidence,
            tool_trace=trace,
        )

    @staticmethod
    def _finalize(
        question_id: str,
        response: FinalResponse,
        trace: list[OperatorTraceEntry],
        evidence: list[ToolEvidence],
    ) -> OperatorResult:
        if response.status != "ANSWERED":
            return OperatorResult(
                question_id=question_id,
                status=response.status,
                answer=response.answer,
                evidence_ids=response.evidence_ids,
                evidence=evidence,
                tool_trace=trace,
            )

        available_ids = {item.id for item in evidence}
        cited = set(response.evidence_ids)
        if not cited or not cited.issubset(available_ids):
            return OperatorResult(
                question_id=question_id,
                status="REJECTED_UNSUPPORTED_EVIDENCE",
                answer=None,
                evidence_ids=sorted(cited),
                evidence=evidence,
                tool_trace=trace,
            )

        return OperatorResult(
            question_id=question_id,
            status="ANSWERED",
            answer=response.answer,
            evidence_ids=response.evidence_ids,
            evidence=evidence,
            tool_trace=trace,
        )

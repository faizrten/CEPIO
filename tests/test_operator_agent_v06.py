from __future__ import annotations

import inspect

from cepio.mcp import MCPFacade
from cepio.model import OntologyObject
from cepio.operator_agent import (
    ConstrainedOperatorAgent,
    FinalResponse,
    MCPToolGateway,
    OperatorTraceEntry,
    RESTToolGateway,
    RestGatewaySettings,
    ToolRequest,
)
from cepio.runtime import CEPIORuntime


class ReadThenAnswerPlanner:
    def __init__(self, object_id: str) -> None:
        self.object_id = object_id

    def next_step(self, *, question_id, question, tools, trace):
        if not trace:
            return ToolRequest(name="cepio_get_object", arguments={"object_id": self.object_id})
        evidence = trace[-1].evidence
        assert evidence is not None
        return FinalResponse(
            status="ANSWERED",
            answer=f"{evidence.payload['name']} is {evidence.payload['properties']['status']}",
            evidence_ids=[evidence.id],
        )


class FabricatedCitationPlanner:
    def __init__(self, object_id: str) -> None:
        self.object_id = object_id

    def next_step(self, *, question_id, question, tools, trace):
        if not trace:
            return ToolRequest(name="cepio_get_object", arguments={"object_id": self.object_id})
        return FinalResponse(
            status="ANSWERED",
            answer="This sounds plausible but cites evidence CEPIO never returned.",
            evidence_ids=["invented-evidence-id"],
        )


class ForbiddenSourcePlanner:
    def next_step(self, *, question_id, question, tools, trace):
        if not trace:
            return ToolRequest(name="web_search", arguments={"query": question})
        return FinalResponse(status="INSUFFICIENT_CEPIO_EVIDENCE")


def _runtime_with_object() -> CEPIORuntime:
    runtime = CEPIORuntime()
    runtime.upsert_object(
        OntologyObject(
            id="UNIT-001",
            type="https://cepio.org/ontology/process#ProcessUnit",
            name="Reference Process Unit",
            properties={"status": "RUNNING"},
        )
    )
    return runtime


def test_operator_has_no_direct_runtime_dependency():
    parameters = inspect.signature(ConstrainedOperatorAgent.__init__).parameters
    assert "runtime" not in parameters
    assert {"gateway", "planner", "max_tool_steps"}.issubset(parameters)


def test_operator_answers_only_from_mcp_tool_evidence():
    runtime = _runtime_with_object()
    facade = MCPFacade(runtime, actor_id="operator-1", actor_roles={"operator"})
    agent = ConstrainedOperatorAgent(
        gateway=MCPToolGateway(facade),
        planner=ReadThenAnswerPlanner("UNIT-001"),
    )

    result = agent.run(question_id="OP-001", question="What is the process unit status?")

    assert result.status == "ANSWERED"
    assert result.answer == "Reference Process Unit is RUNNING"
    assert len(result.evidence) == 1
    assert result.evidence_ids == [result.evidence[0].id]
    assert result.tool_trace[0].request.name == "cepio_get_object"


def test_operator_rejects_fabricated_citation_even_after_valid_tool_call():
    runtime = _runtime_with_object()
    facade = MCPFacade(runtime, actor_id="operator-1", actor_roles={"operator"})
    agent = ConstrainedOperatorAgent(
        gateway=MCPToolGateway(facade),
        planner=FabricatedCitationPlanner("UNIT-001"),
    )

    result = agent.run(question_id="OP-002", question="What is the process unit status?")

    assert result.status == "REJECTED_UNSUPPORTED_EVIDENCE"
    assert result.answer is None
    assert result.evidence_ids == ["invented-evidence-id"]
    assert len(result.evidence) == 1


def test_operator_cannot_use_a_non_cepio_truth_source():
    runtime = _runtime_with_object()
    facade = MCPFacade(runtime, actor_id="operator-1", actor_roles={"operator"})
    agent = ConstrainedOperatorAgent(
        gateway=MCPToolGateway(facade),
        planner=ForbiddenSourcePlanner(),
    )

    result = agent.run(question_id="OP-003", question="Search the web for this unit state")

    assert result.status == "INSUFFICIENT_CEPIO_EVIDENCE"
    assert result.tool_trace[0].evidence is None
    assert "not exposed by CEPIO gateway" in (result.tool_trace[0].error or "")


def test_rest_gateway_uses_public_cepio_endpoint_and_preserves_auth_header():
    calls = []

    def transport(method: str, path: str, body, headers):
        calls.append((method, path, body, headers))
        return {
            "id": "UNIT-REST-001",
            "type": "https://cepio.org/ontology/process#ProcessUnit",
            "name": "REST Process Unit",
            "properties": {"status": "RUNNING"},
            "interfaces": [],
            "version": 1,
            "created_at": "2026-10-17T00:00:00Z",
            "updated_at": "2026-10-17T00:00:00Z",
        }

    gateway = RESTToolGateway(
        RestGatewaySettings(base_url="https://cepio.example", bearer_token="test-token"),
        transport=transport,
    )
    agent = ConstrainedOperatorAgent(
        gateway=gateway,
        planner=ReadThenAnswerPlanner("UNIT-REST-001"),
    )

    result = agent.run(question_id="OP-004", question="What is the unit status?")

    assert result.status == "ANSWERED"
    assert calls == [
        (
            "GET",
            "/objects/UNIT-REST-001",
            None,
            {"Accept": "application/json", "Authorization": "Bearer test-token"},
        )
    ]


def test_operator_tool_evidence_ids_are_stable_for_same_cepio_result():
    runtime = _runtime_with_object()
    facade = MCPFacade(runtime, actor_id="operator-1", actor_roles={"operator"})

    first = ConstrainedOperatorAgent(
        gateway=MCPToolGateway(facade),
        planner=ReadThenAnswerPlanner("UNIT-001"),
    ).run(question_id="OP-005", question="Status?")
    second = ConstrainedOperatorAgent(
        gateway=MCPToolGateway(facade),
        planner=ReadThenAnswerPlanner("UNIT-001"),
    ).run(question_id="OP-005", question="Status?")

    assert first.evidence[0].id == second.evidence[0].id

import json

import httpx
import pytest

from cepio.nemotron_planner import NemotronPlanner, NemotronSettings
from cepio.operator_agent import ConstrainedOperatorAgent, OperatorTraceEntry, ToolRequest


def envelope(value, finish="stop"):
    return {"choices": [{"finish_reason": finish, "message": {"content": json.dumps(value)}}]}


def planner(handler, **kwargs):
    return NemotronPlanner(
        NemotronSettings(
            base_url="https://model.example/v1", model="pinned-nemotron", enabled=True, **kwargs
        ),
        transport=httpx.MockTransport(handler),
    )


def run_step(p):
    return p.next_step(
        question_id="q",
        question="Investigate asset A",
        tools=[{"name": "cepio_get_object"}],
        trace=[],
    )


def test_disabled_never_calls_transport():
    p = NemotronPlanner(
        NemotronSettings(base_url="http://localhost:8000/v1", model="test"),
        transport=httpx.MockTransport(lambda r: pytest.fail("network")),
    )
    assert run_step(p).status == "INSUFFICIENT_CEPIO_EVIDENCE"


@pytest.mark.parametrize(
    "url",
    [
        "http://remote/v1",
        "https://user:pass@host/v1",
        "https://host/v1?key=secret",
        "file:///tmp/model",
    ],
)
def test_unsafe_endpoint(url):
    with pytest.raises(ValueError):
        NemotronPlanner(NemotronSettings(base_url=url, model="test"))


@pytest.mark.parametrize(
    "value",
    [
        {"kind": "tool", "name": "cepio_execute_action", "arguments": {}},
        {
            "kind": "tool",
            "name": "cepio_get_object",
            "arguments": {"object_id": "A", "actor": "admin"},
        },
        {"kind": "tool", "name": "cepio_get_object", "arguments": {"object_id": 123}},
        {"kind": "tool", "name": "cepio_neighbors", "arguments": {"object_id": "A"}},
        {"kind": "final", "status": "ANSWERED", "answer": "Invented", "evidence_ids": ["fake"]},
        {"kind": "final", "status": "ANSWERED", "answer": "Unsupported", "evidence_ids": []},
        {
            "kind": "final",
            "status": "INSUFFICIENT_CEPIO_EVIDENCE",
            "answer": "Invented",
            "evidence_ids": [],
        },
        {"kind": "other"},
    ],
)
def test_rejects_unsafe_or_unsupported_output(value):
    result = run_step(planner(lambda r: httpx.Response(200, json=envelope(value))))
    assert result.status == "INSUFFICIENT_CEPIO_EVIDENCE"
    assert result.answer is None


@pytest.mark.parametrize(
    "mode", ["timeout", "redirect", "error", "malformed", "truncated", "oversize"]
)
def test_transport_failures_abstain(mode):
    def handler(request):
        if mode == "timeout":
            raise httpx.ReadTimeout("secret", request=request)
        if mode == "redirect":
            return httpx.Response(302, headers={"location": "https://other.example"})
        if mode == "error":
            return httpx.Response(500, text="secret")
        if mode == "oversize":
            return httpx.Response(200, content=b"x" * 1048577)
        if mode == "truncated":
            return httpx.Response(200, json=envelope({}, "length"))
        return httpx.Response(200, text="not json")

    assert run_step(planner(handler)).status == "INSUFFICIENT_CEPIO_EVIDENCE"


def test_input_limit_prevents_call():
    p = planner(lambda r: pytest.fail("network"), max_input_bytes=1)
    assert run_step(p).status == "INSUFFICIENT_CEPIO_EVIDENCE"


def test_write_trace_never_leaves_host():
    p = planner(lambda r: pytest.fail("network"))
    result = p.next_step(
        question_id="q",
        question="read",
        tools=[],
        trace=[OperatorTraceEntry(step=1, request=ToolRequest(name="cepio_execute_action"))],
    )
    assert result.status == "INSUFFICIENT_CEPIO_EVIDENCE"


def test_secret_not_in_settings_repr():
    settings = NemotronSettings(
        base_url="https://model.example/v1", model="test", api_key="never-display-me"
    )
    assert "never-display-me" not in repr(settings)


def test_configured_credential_is_sent_only_in_authorization_header():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer test-only-credential"
        assert request.url == "https://model.example/v1/chat/completions"
        assert b"test-only-credential" not in request.content
        return httpx.Response(
            200,
            json=envelope(
                {"kind": "tool", "name": "cepio_get_object", "arguments": {"object_id": "A"}}
            ),
        )

    result = run_step(planner(handler, api_key="test-only-credential"))
    assert result.name == "cepio_get_object"


def test_native_tool_calls_cannot_bypass_validation():
    response = envelope(
        {"kind": "tool", "name": "cepio_get_object", "arguments": {"object_id": "A"}}
    )
    response["choices"][0]["message"]["tool_calls"] = [{"name": "cepio_execute_action"}]
    assert run_step(planner(lambda r: httpx.Response(200, json=response))).status == (
        "INSUFFICIENT_CEPIO_EVIDENCE"
    )


def test_malformed_message_abstains():
    response = {"choices": [{"finish_reason": "stop", "message": []}]}
    assert run_step(planner(lambda r: httpx.Response(200, json=response))).status == (
        "INSUFFICIENT_CEPIO_EVIDENCE"
    )


def test_existing_operator_end_to_end():
    calls = []

    class Gateway:
        def list_tools(self):
            return [{"name": "cepio_get_object"}, {"name": "cepio_execute_action"}]

        def call_tool(self, name, arguments):
            calls.append((name, arguments))
            return {"asset": "A", "observation": "synthetic inspection required"}

    def handler(request):
        payload = json.loads(request.content)
        assert payload["model"] == "pinned-nemotron"
        assert payload["max_tokens"] == 2048
        context = json.loads(payload["messages"][1]["content"])
        assert [t["name"] for t in context["tools"]] == ["cepio_get_object"]
        if not context["trace"]:
            result = {"kind": "tool", "name": "cepio_get_object", "arguments": {"object_id": "A"}}
        else:
            result = {
                "kind": "final",
                "status": "ANSWERED",
                "answer": "Inspection required.",
                "evidence_ids": [context["trace"][0]["evidence"]["id"]],
            }
        return httpx.Response(200, json=envelope(result))

    result = ConstrainedOperatorAgent(gateway=Gateway(), planner=planner(handler)).run(
        question_id="synthetic", question="Inspect A"
    )
    assert result.status == "ANSWERED"
    assert len(result.evidence_ids) == 1
    assert calls == [("cepio_get_object", {"object_id": "A"})]

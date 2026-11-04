from __future__ import annotations

import httpx
import pytest

from cepio.adapters import (
    AdapterVerificationStatus,
    GovernedVerificationRequest,
    GovernedWriteRequest,
)
from cepio.teams_workflow import (
    TEAMS_ATTENTION_OPERATION,
    TEAMS_WORKFLOW_SYSTEM,
    TeamsAttentionEvent,
    TeamsAttentionSeverity,
    TeamsWebhookResponse,
    TeamsWorkflowWebhookAdapter,
    _post_json,
    build_teams_attention_payload,
)


def _event(**overrides):
    values = {
        "title": "Compressor C-201 needs attention",
        "summary": "Bearing vibration increased 18% over the last six hours.",
        "severity": TeamsAttentionSeverity.high,
        "subject_id": "compressor-c201",
        "subject_type": "Equipment",
        "subject_label": "Compressor C-201",
        "recommendation": "Inspect within 24 hours.",
        "impact": "Potential 1.8% throughput exposure",
        "confidence": 0.83,
        "evidence": ["PI vibration trend", "SAP maintenance history"],
        "context_url": "https://industry-iq.example/objects/compressor-c201",
    }
    values.update(overrides)
    return TeamsAttentionEvent(**values)


def _write_request(payload):
    return GovernedWriteRequest(
        execution_id="exec-1",
        system=TEAMS_WORKFLOW_SYSTEM,
        operation=TEAMS_ATTENTION_OPERATION,
        external_id="operations-channel",
        canonical_object_id="compressor-c201",
        action_id="action-1",
        actor_id="cepio-runtime",
        decision_id="decision-1",
        idempotency_key="teams:action-1",
        payload=payload,
    )


def _verification_request():
    return GovernedVerificationRequest(
        execution_id="exec-1",
        system=TEAMS_WORKFLOW_SYSTEM,
        operation=TEAMS_ATTENTION_OPERATION,
        external_id="operations-channel",
        canonical_object_id="compressor-c201",
        action_id="action-1",
        idempotency_key="teams:action-1",
        source_request_id="FLOW-123",
        expected_payload={},
    )


def test_attention_payload_projects_event_to_adaptive_card():
    payload = build_teams_attention_payload(_event())

    assert payload["schema_version"] == "0.1"
    assert payload["event"]["severity"] == "high"
    card = payload["adaptive_card"]
    assert card["type"] == "AdaptiveCard"
    assert card["version"] == "1.5"
    assert card["actions"][0]["type"] == "Action.OpenUrl"
    assert "SAP maintenance history" in str(card["body"])


def test_minimal_attention_card_omits_optional_sections():
    payload = build_teams_attention_payload(
        _event(
            subject_label=None,
            recommendation=None,
            impact=None,
            confidence=None,
            evidence=[],
            context_url=None,
        )
    )

    card = payload["adaptive_card"]
    assert "actions" not in card
    assert "Recommended action" not in str(card["body"])
    assert "Evidence" not in str(card["body"])
    assert "Equipment · compressor-c201" in str(card["body"])


def test_attention_urls_fail_closed_to_https_and_secret_url_shape():
    with pytest.raises(ValueError, match="absolute HTTPS"):
        _event(context_url="http://industry-iq.example/object")

    with pytest.raises(ValueError, match="absolute HTTPS"):
        TeamsWorkflowWebhookAdapter("http://workflow.example/hook")

    with pytest.raises(ValueError, match="userinfo or a fragment"):
        TeamsWorkflowWebhookAdapter("https://user:password@workflow.example/hook")

    with pytest.raises(ValueError, match="userinfo or a fragment"):
        TeamsWorkflowWebhookAdapter("https://workflow.example/hook#secret")


def test_post_json_returns_safe_transport_receipt(monkeypatch):
    request = httpx.Request("POST", "https://workflow.example/hook")
    response = httpx.Response(
        202,
        request=request,
        headers={"x-ms-workflow-run-id": "FLOW-123"},
    )

    def post(*args, **kwargs):
        assert args[0] == "https://workflow.example/hook"
        assert kwargs["follow_redirects"] is False
        return response

    monkeypatch.setattr("cepio.teams_workflow.httpx.post", post)
    receipt = _post_json(
        "https://workflow.example/hook",
        {"hello": "world"},
        {"Content-Type": "application/json"},
        3.0,
    )

    assert receipt == TeamsWebhookResponse(status_code=202, request_id="FLOW-123")


def test_post_json_sanitizes_http_and_transport_failures(monkeypatch):
    request = httpx.Request("POST", "https://workflow.example/secret-token")
    rejected = httpx.Response(503, request=request)

    monkeypatch.setattr("cepio.teams_workflow.httpx.post", lambda *_, **__: rejected)
    with pytest.raises(RuntimeError, match="HTTP 503") as status_error:
        _post_json(
            "https://workflow.example/secret-token",
            {},
            {"Content-Type": "application/json"},
            3.0,
        )
    assert "secret-token" not in str(status_error.value)

    def transport_failure(*_, **__):
        raise httpx.ConnectError("connection failed", request=request)

    monkeypatch.setattr("cepio.teams_workflow.httpx.post", transport_failure)
    with pytest.raises(RuntimeError, match="transport failed") as transport_error:
        _post_json(
            "https://workflow.example/secret-token",
            {},
            {"Content-Type": "application/json"},
            3.0,
        )
    assert "secret-token" not in str(transport_error.value)


def test_adapter_posts_once_and_never_discloses_webhook_secret():
    calls = []
    secret_url = "https://workflow.example/hooks/super-secret-token"

    def transport(url, payload, headers, timeout):
        calls.append((url, payload, headers, timeout))
        return TeamsWebhookResponse(status_code=202, request_id="FLOW-123")

    adapter = TeamsWorkflowWebhookAdapter(secret_url, transport=transport)
    request = _write_request(build_teams_attention_payload(_event()))

    first = adapter.write_governed(request)
    second = adapter.write_governed(request)

    assert len(calls) == 1
    assert calls[0][0] == secret_url
    posted = calls[0][1]
    assert set(posted) == {"type", "attachments"}
    assert posted["type"] == "message"
    assert len(posted["attachments"]) == 1
    attachment = posted["attachments"][0]
    assert attachment["contentType"] == "application/vnd.microsoft.card.adaptive"
    assert attachment["contentUrl"] is None
    assert attachment["content"]["type"] == "AdaptiveCard"
    assert attachment["content"]["body"][1]["text"] == "Compressor C-201 needs attention"
    assert "operations-channel" not in str(posted)
    assert calls[0][2]["X-CEPIO-Idempotency-Key"] == "teams:action-1"
    assert first == second
    assert first.source_request_id == "FLOW-123"
    assert first.source_payload["http_status"] == 202
    assert secret_url not in first.model_dump_json()


def test_adapter_generates_non_secret_request_id_when_provider_omits_one():
    adapter = TeamsWorkflowWebhookAdapter(
        "https://workflow.example/hooks/secret-token",
        transport=lambda *_: TeamsWebhookResponse(status_code=202),
    )

    receipt = adapter.write_governed(_write_request(build_teams_attention_payload(_event())))

    assert receipt.source_request_id.startswith("TEAMS-")
    assert "secret-token" not in receipt.model_dump_json()


def test_adapter_transport_acknowledgement_is_not_delivery_verification():
    adapter = TeamsWorkflowWebhookAdapter(
        "https://workflow.example/hooks/token",
        transport=lambda *_: TeamsWebhookResponse(status_code=200, request_id="FLOW-123"),
    )
    verification = _verification_request()

    before = adapter.verify_write(verification)
    assert before.status == AdapterVerificationStatus.not_applied

    adapter.write_governed(_write_request(build_teams_attention_payload(_event())))
    after = adapter.verify_write(verification)
    assert after.status == AdapterVerificationStatus.unknown
    assert "end-to-end" in (after.message or "")
    assert adapter.reconcile_write(verification).status == AdapterVerificationStatus.unknown


def test_adapter_rejects_wrong_system_or_operation():
    adapter = TeamsWorkflowWebhookAdapter(
        "https://workflow.example/hooks/token",
        transport=lambda *_: TeamsWebhookResponse(status_code=200),
    )
    payload = build_teams_attention_payload(_event())

    wrong_system = _write_request(payload).model_copy(update={"system": "sap"})
    with pytest.raises(ValueError, match="cannot handle system"):
        adapter.write_governed(wrong_system)

    wrong_operation = _write_request(payload).model_copy(update={"operation": "approve"})
    with pytest.raises(ValueError, match="does not support operation"):
        adapter.write_governed(wrong_operation)

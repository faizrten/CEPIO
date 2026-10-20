from __future__ import annotations

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


def test_attention_urls_fail_closed_to_https():
    with pytest.raises(ValueError, match="absolute HTTPS"):
        _event(context_url="http://industry-iq.example/object")

    with pytest.raises(ValueError, match="absolute HTTPS"):
        TeamsWorkflowWebhookAdapter("http://workflow.example/hook")


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
    assert calls[0][1]["cepio"]["destination"] == "operations-channel"
    assert calls[0][2]["X-CEPIO-Idempotency-Key"] == "teams:action-1"
    assert first == second
    assert first.source_request_id == "FLOW-123"
    assert first.source_payload["http_status"] == 202
    assert secret_url not in first.model_dump_json()


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

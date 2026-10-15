import json

import pytest

from cepio.bootstrap import build_runtime
from cepio.model import ActionRequest, ObjectRef, OntologyObject
from cepio.observability import InMemoryTelemetrySink
from cepio.runtime import AuthorizationError


def _runtime_with_sink():
    sink = InMemoryTelemetrySink()
    runtime = build_runtime(
        validate_types=False,
        validate_properties=False,
        telemetry_sink=sink,
    )
    return runtime, sink


def test_repository_function_policy_and_action_telemetry_are_captured():
    runtime, sink = _runtime_with_sink()
    runtime.upsert_object(
        OntologyObject(
            id="K-201",
            type="Compressor",
            name="K-201",
            properties={"criticality": "high", "secret_note": "do-not-export"},
            interfaces={"MaintainableAsset"},
        )
    )

    risk = runtime.call_function("calculateAssetRisk", asset_id="K-201")
    assert risk > 0

    result = runtime.execute_action(
        ActionRequest(
            action_type="CreateWorkOrder",
            target=ObjectRef(id="K-201", type="Compressor"),
            actor_id="maintenance-user",
            actor_roles={"maintenance_engineer"},
            parameters={"secret": "do-not-export"},
        )
    )
    assert result.status.value == "executed"

    categories = {event.category for event in sink.events}
    assert {"repository", "function", "policy", "action"}.issubset(categories)
    assert all(event.duration_ms >= 0 for event in sink.events)
    assert any(
        event.category == "function" and event.operation == "calculateAssetRisk" and event.success
        for event in sink.events
    )
    assert any(
        event.category == "action" and event.operation == "CreateWorkOrder" and event.success
        for event in sink.events
    )

    encoded = json.dumps([event.attributes for event in sink.events])
    assert "do-not-export" not in encoded
    assert "secret_note" not in encoded
    assert "criticality" not in encoded


def test_rejected_action_emits_sanitized_telemetry():
    runtime, sink = _runtime_with_sink()
    runtime.upsert_object(
        OntologyObject(
            id="K-201",
            type="Compressor",
            name="K-201",
            properties={"confidential": "classified-value"},
            interfaces={"MaintainableAsset"},
        )
    )

    with pytest.raises(AuthorizationError):
        runtime.execute_action(
            ActionRequest(
                action_type="CreateWorkOrder",
                target=ObjectRef(id="K-201", type="Compressor"),
                actor_id="agent-1",
                actor_roles={"ai_agent_recommender"},
                parameters={"private_instruction": "classified-value"},
            )
        )

    rejected = [
        event
        for event in sink.events
        if event.category == "action" and event.attributes.get("outcome") == "rejected"
    ]
    assert len(rejected) == 1
    assert rejected[0].success is False
    assert rejected[0].attributes["policy_effect"] in {"deny", "recommend_only", "approval_required"}

    encoded = json.dumps([event.attributes for event in sink.events])
    assert "classified-value" not in encoded
    assert "private_instruction" not in encoded
    assert "confidential" not in encoded


def test_repository_failure_is_observable_without_argument_payloads():
    runtime, sink = _runtime_with_sink()

    with pytest.raises(KeyError):
        runtime.get_object("missing-object")

    get_events = [
        event
        for event in sink.events
        if event.category == "repository" and event.operation == "get_object"
    ]
    assert get_events
    assert get_events[-1].success is True
    assert set(get_events[-1].attributes) == {"repository_kind"}

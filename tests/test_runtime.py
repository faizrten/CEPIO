import pytest

from cepio.bootstrap import build_runtime
from cepio.model import ActionRequest, ObjectRef, OntologyObject, OperationalEvent
from cepio.runtime import AuthorizationError


def test_governed_action_and_function():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="K-201",
            type="Compressor",
            name="K-201",
            properties={"criticality": "high"},
            interfaces={"MaintainableAsset"},
        )
    )
    runtime.record_event(
        OperationalEvent(type="TripEvent", subject=ObjectRef(id="K-201", type="Compressor"))
    )
    assert runtime.call_function("calculateAssetRisk", asset_id="K-201") > 0.5

    result = runtime.execute_action(
        ActionRequest(
            action_type="CreateWorkOrder",
            target=ObjectRef(id="K-201", type="Compressor"),
            actor_id="m1",
            actor_roles={"maintenance_engineer"},
        )
    )
    assert result.status.value == "executed"
    assert len(runtime.neighbors("K-201", "hasWorkOrder")) == 1


def test_unauthorized_action_fails_closed():
    runtime = build_runtime()
    runtime.upsert_object(OntologyObject(id="K-201", type="Compressor", name="K-201"))
    with pytest.raises(AuthorizationError):
        runtime.execute_action(
            ActionRequest(
                action_type="CreateWorkOrder",
                target=ObjectRef(id="K-201", type="Compressor"),
                actor_id="agent-1",
                actor_roles={"ai_agent_recommender"},
            )
        )

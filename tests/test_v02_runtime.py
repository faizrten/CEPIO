from __future__ import annotations

from pathlib import Path

import pytest

from cepio.bootstrap import build_runtime
from cepio.mcp import MCPFacade
from cepio.model import ActionRequest, Decision, ObjectRef, OntologyObject, Relationship
from cepio.repositories import ConcurrencyError
from cepio.runtime import AuthorizationError


def compressor() -> OntologyObject:
    return OntologyObject(
        id="K-201",
        type="Compressor",
        name="Recycle Gas Compressor K-201",
        properties={
            "criticality": "high",
            "operatingState": "degraded",
            "replacementValueUSD": 8_200_000,
        },
        interfaces={"MaintainableAsset", "Inspectable", "RiskBearing"},
    )


def test_sqlite_persistence_and_optimistic_concurrency(tmp_path: Path):
    db = tmp_path / "cepio.db"
    runtime = build_runtime(sqlite_path=db)
    first = runtime.upsert_object(compressor())
    assert first.version == 1

    updated = first.model_copy(deep=True)
    updated.properties["operatingState"] = "normal"
    second = runtime.upsert_object(updated, expected_version=1)
    assert second.version == 2

    stale = first.model_copy(deep=True)
    stale.properties["operatingState"] = "failed"
    with pytest.raises(ConcurrencyError):
        runtime.upsert_object(stale, expected_version=1)

    runtime.object_repository.close()  # type: ignore[attr-defined]
    reloaded = build_runtime(sqlite_path=db)
    persisted = reloaded.get_object("K-201")
    assert persisted.version == 2
    assert persisted.properties["operatingState"] == "normal"
    reloaded.object_repository.close()  # type: ignore[attr-defined]


def test_idempotency_is_scoped_and_every_attempt_is_audited():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    request = ActionRequest(
        action_type="CreateWorkOrder",
        target=ObjectRef(id="K-201", type="Compressor"),
        actor_id="m1",
        actor_roles={"maintenance_engineer"},
        idempotency_key="bearing-inspection-001",
    )

    first = runtime.execute_action(request)
    second = runtime.execute_action(request)
    assert first.status.value == "executed"
    assert second.replayed is True
    assert second.action_id == first.action_id
    assert len(runtime.neighbors("K-201", "hasWorkOrder")) == 1
    assert len(runtime.all_audits()) == 2
    assert runtime.all_audits()[-1].replayed is True

    with pytest.raises(AuthorizationError):
        runtime.execute_action(
            request.model_copy(update={"actor_id": "agent-1", "actor_roles": {"ai_agent_recommender"}})
        )
    assert len(runtime.all_audits()) == 3
    assert runtime.all_audits()[-1].status.value == "rejected"


def test_preconditions_fail_closed_and_are_audited():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(id="K-202", type="Compressor", name="K-202", interfaces={"RiskBearing"})
    )
    result = runtime.execute_action(
        ActionRequest(
            action_type="CreateWorkOrder",
            target=ObjectRef(id="K-202", type="Compressor"),
            actor_id="m1",
            actor_roles={"maintenance_engineer"},
        )
    )
    assert result.status.value == "rejected"
    assert "MaintainableAsset" in result.message
    assert len(runtime.all_audits()) == 1
    assert runtime.neighbors("K-202", "hasWorkOrder") == []


def test_decision_record_links_recommendation_to_action():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    decision = runtime.save_decision(
        Decision(
            subject=ObjectRef(id="K-201", type="Compressor"),
            problem="Repeated trips and degraded vibration state",
            observations=["Two recent trips", "Criticality high"],
            recommendation="Inspect bearings before next production campaign",
            recommended_action="CreateInspection",
            confidence=0.88,
            created_by="reliability-agent",
        )
    )
    assert runtime.get_decision(decision.id).recommended_action == "CreateInspection"

    result = runtime.execute_action(
        ActionRequest(
            action_type="CreateInspection",
            target=ObjectRef(id="K-201", type="Compressor"),
            actor_id="reliability-engineer-1",
            actor_roles={"reliability_engineer"},
            decision_id=decision.id,
        )
    )
    assert result.status.value == "executed"
    assert runtime.all_audits()[-1].decision_id == decision.id


def test_registry_enforces_relationship_domain_and_range():
    runtime = build_runtime()
    runtime.upsert_object(OntologyObject(id="HCU-01", type="Hydrocracker", name="Hydrocracker"))
    runtime.upsert_object(OntologyObject(id="WO-1", type="WorkOrder", name="WO-1", interfaces={"WorkItem"}))
    with pytest.raises(ValueError, match="violates domain"):
        runtime.add_relationship(
            Relationship(
                type="hasWorkOrder",
                source=ObjectRef(id="HCU-01", type="Hydrocracker"),
                target=ObjectRef(id="WO-1", type="WorkOrder"),
            )
        )


def test_mcp_facade_filters_agent_properties_and_blocks_execution():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    facade = MCPFacade(runtime, actor_id="agent-1", actor_roles={"ai_agent_recommender"})
    obj = facade.call_tool("cepio_get_object", {"object_id": "K-201"})
    assert obj["properties"]["criticality"] == "high"
    assert "replacementValueUSD" not in obj["properties"]

    result = facade.call_tool(
        "cepio_execute_action",
        {
            "action_type": "CreateWorkOrder",
            "target_id": "K-201",
            "target_type": "Compressor",
            "parameters": {},
            "idempotency_key": "agent-attempt",
        },
    )
    assert result["status"] == "rejected"
    assert runtime.neighbors("K-201", "hasWorkOrder") == []


def test_human_approval_action_updates_work_order_with_versioning():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    created = runtime.execute_action(
        ActionRequest(
            action_type="CreateWorkOrder",
            target=ObjectRef(id="K-201", type="Compressor"),
            actor_id="m1",
            actor_roles={"maintenance_engineer"},
            parameters={"work_order_id": "WO-DEF-1"},
        )
    )
    assert created.status.value == "executed"
    before = runtime.get_object("WO-DEF-1")
    assert before.version == 1

    approved = runtime.execute_action(
        ActionRequest(
            action_type="ApproveMaintenanceDeferral",
            target=ObjectRef(id="WO-DEF-1", type="WorkOrder"),
            actor_id="manager-1",
            actor_roles={"maintenance_manager"},
            parameters={"reason": "Spare bearing unavailable", "until": "2026-11-15"},
        )
    )
    assert approved.status.value == "executed"
    after = runtime.get_object("WO-DEF-1")
    assert after.version == 2
    assert after.properties["status"] == "deferred"


def test_escalate_risk_exposes_compensation_metadata():
    runtime = build_runtime()
    runtime.upsert_object(compressor())
    result = runtime.execute_action(
        ActionRequest(
            action_type="EscalateRisk",
            target=ObjectRef(id="K-201", type="Compressor"),
            actor_id="r1",
            actor_roles={"reliability_engineer"},
            parameters={"risk_status": "critical"},
        )
    )
    assert result.status.value == "executed"
    assert result.compensation and result.compensation["available"] is True
    assert runtime.get_object("K-201").properties["riskStatus"] == "critical"

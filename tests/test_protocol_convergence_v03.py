from __future__ import annotations

import asyncio
from typing import Any

import httpx
from fastapi.testclient import TestClient

from cepio import api as legacy_api
from cepio.application_contract import (
    ContractMetadata,
    EvidenceReference,
    EvidenceRole,
    ExecutionContext,
    SkillEvaluation,
    SkillInvocation,
)
from cepio.application_runtime import build_application_service
from cepio.bootstrap import build_runtime
from cepio.integrations.microsoft.foundry_gateway import ActorContext, FixedActorProvider
from cepio.integrations.microsoft.foundry_mcp import build_mcp_server
from cepio.maintenance_deferral_skill import MAINTENANCE_DEFERRAL_SKILL_ID
from cepio.model import ObjectRef, OntologyObject, Relationship
from cepio.public_api import app
from cepio.sdk import CEPIOClient


def _seed_runtime():
    runtime = build_runtime()
    equipment = OntologyObject(id="P-CONV", type="Pump", name="P-CONV")
    work_order = OntologyObject(
        id="WO-CONV",
        type="WorkOrder",
        name="Seal replacement",
        properties={"status": "planned", "priority": "high"},
    )
    risk = OntologyObject(
        id="RISK-CONV",
        type="Risk",
        name="Deferral risk",
        properties={
            "currentRiskScore": 0.31,
            "deferralRiskScore": 0.52,
            "maxSupportedDeferralHours": 168.0,
            "hardConstraint": False,
        },
    )
    observation = OntologyObject(
        id="OBS-CONV",
        type="ConditionObservation",
        name="Condition evidence",
        properties={"severity": "moderate"},
    )
    for obj in (equipment, work_order, risk, observation):
        runtime.upsert_object(obj)
    runtime.add_relationship(
        Relationship(
            type="hasWorkOrder",
            source=ObjectRef(id=equipment.id, type=equipment.type),
            target=ObjectRef(id=work_order.id, type=work_order.type),
        )
    )
    runtime.add_relationship(
        Relationship(
            type="hasRisk",
            source=ObjectRef(id=equipment.id, type=equipment.type),
            target=ObjectRef(id=risk.id, type=risk.type),
        )
    )
    runtime.add_relationship(
        Relationship(
            type="hasConditionObservation",
            source=ObjectRef(id=equipment.id, type=equipment.type),
            target=ObjectRef(id=observation.id, type=observation.type),
        )
    )
    return runtime


def _invocation() -> SkillInvocation:
    return SkillInvocation(
        skill_id=MAINTENANCE_DEFERRAL_SKILL_ID,
        subject=ObjectRef(id="P-CONV", type="Pump"),
        parameters={
            "work_order_id": "WO-CONV",
            "risk_id": "RISK-CONV",
            "proposed_deferral_hours": 120.0,
        },
        evidence=[
            EvidenceReference(
                object_ref=ObjectRef(id="OBS-CONV", type="ConditionObservation"),
                role=EvidenceRole.supporting,
                provenance_ref="prov:conv-obs",
            ),
            EvidenceReference(
                object_ref=ObjectRef(id="RISK-CONV", type="Risk"),
                role=EvidenceRole.supporting,
            ),
        ],
        assessment_refs=[ObjectRef(id="RISK-CONV", type="Risk")],
        metadata=ContractMetadata(correlation_id="corr-convergence-v03"),
    )


def _semantic_payload(evaluation: SkillEvaluation) -> dict[str, Any]:
    payload = evaluation.model_dump(mode="json")
    decision = payload.get("decision")
    if isinstance(decision, dict):
        decision.pop("id", None)
        decision.pop("created_at", None)
        decision.pop("updated_at", None)
    return payload


def _sdk_transport(rest_client: TestClient) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        response = rest_client.request(
            request.method,
            request.url.path,
            headers=dict(request.headers),
            content=request.content,
        )
        return httpx.Response(
            response.status_code,
            headers=dict(response.headers),
            content=response.content,
            request=request,
        )

    return httpx.MockTransport(handler)


def test_skill_evaluation_converges_across_direct_rest_sdk_and_mcp(monkeypatch):
    from mcp import Client

    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")

    runtime = _seed_runtime()
    monkeypatch.setattr(legacy_api, "runtime", runtime)
    invocation = _invocation()

    direct_service = build_application_service(runtime)
    direct = direct_service.evaluate_skill(
        invocation,
        ExecutionContext(
            actor_id="agent-convergence-01",
            actor_roles=frozenset({"ai_agent_recommender"}),
            tenant_id="dev",
        ),
    )

    with TestClient(app) as rest_client:
        rest_response = rest_client.post(
            "/api/v1/skills/evaluate",
            headers={
                "X-CEPIO-Dev-Actor": "agent-convergence-01",
                "X-CEPIO-Dev-Roles": "ai_agent_recommender",
            },
            json=invocation.model_dump(mode="json"),
        )
        assert rest_response.status_code == 200
        rest = SkillEvaluation.model_validate(rest_response.json())

        sdk = CEPIOClient(
            "http://testserver",
            dev_actor="agent-convergence-01",
            dev_roles={"ai_agent_recommender"},
            transport=_sdk_transport(rest_client),
        )
        try:
            sdk_result = sdk.evaluate_skill(invocation)
        finally:
            sdk.close()

    actor = ActorContext(
        subject_id="agent-convergence-01",
        roles={"ai_agent_recommender"},
        principal_type="agent",
        auth_mode="development",
        tenant_id="dev",
    )
    server = build_mcp_server(runtime, FixedActorProvider(actor))

    async def _via_mcp() -> SkillEvaluation:
        async with Client(server, raise_exceptions=True) as client:
            listed = await client.list_tools()
            tools = {tool.name: tool for tool in listed.tools}
            skill_tool = tools["cepio_evaluate_skill"]
            properties = skill_tool.input_schema.get("properties", {})
            assert "actor_id" not in properties
            assert "actor_roles" not in properties

            result = await client.call_tool(
                "cepio_evaluate_skill",
                {"invocation": invocation.model_dump(mode="json")},
            )
            assert result.is_error is False
            return SkillEvaluation.model_validate(result.structured_content)

    mcp_result = asyncio.run(_via_mcp())

    expected = _semantic_payload(direct)
    assert _semantic_payload(rest) == expected
    assert _semantic_payload(sdk_result) == expected
    assert _semantic_payload(mcp_result) == expected

    assert direct.status.value == "completed"
    assert direct.decision is not None
    assert direct.decision.created_by == "agent-convergence-01"
    assert direct.decision.recommended_action == "DeferWorkOrder"
    assert runtime.get_object("WO-CONV").properties["status"] == "planned"


def test_rest_skill_invocation_cannot_supply_actor_authority(monkeypatch):
    monkeypatch.setenv("CEPIO_ENVIRONMENT", "test")
    monkeypatch.setenv("CEPIO_AUTH_MODE", "dev")

    runtime = _seed_runtime()
    monkeypatch.setattr(legacy_api, "runtime", runtime)
    payload = _invocation().model_dump(mode="json")
    payload["actor_id"] = "spoofed-actor"
    payload["actor_roles"] = ["maintenance_manager"]

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/skills/evaluate",
            headers={
                "X-CEPIO-Dev-Actor": "agent-convergence-01",
                "X-CEPIO-Dev-Roles": "ai_agent_recommender",
            },
            json=payload,
        )

    assert response.status_code == 200
    evaluation = SkillEvaluation.model_validate(response.json())
    assert evaluation.decision is not None
    assert evaluation.decision.created_by == "agent-convergence-01"
    assert runtime.get_object("WO-CONV").properties["status"] == "planned"

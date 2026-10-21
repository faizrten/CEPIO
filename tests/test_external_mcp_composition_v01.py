from __future__ import annotations

import asyncio

import pytest

from cepio.application_contract import (
    CEPIOApplicationService,
    DecisionProposal,
    EvidenceReference,
    EvidenceRole,
    SkillExecutionOutput,
    SkillInvocation,
)
from cepio.bootstrap import build_runtime
from cepio.integrations.microsoft.foundry_gateway import (
    ActorContext,
    CEPIOMCPGateway,
    FixedActorProvider,
)
from cepio.integrations.microsoft.foundry_mcp import (
    build_mcp_server,
    build_mcp_server_with_application_service,
)
from cepio.integrations.microsoft.hosted_mcp import (
    build_hosted_mcp_with_application_service,
)
from cepio.model import ObjectRef, OntologyObject
from cepio.skill_preflight import SkillAuthorityContract, SkillPreflightSpec, SkillRegistry

SKILL_ID = "cepio.skill.synthetic.external-evidence-review"


def _composed_service():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="WO-EXT",
            type="WorkOrder",
            name="External review work order",
            properties={"status": "planned"},
        )
    )
    skills = SkillRegistry(runtime)
    skills.register(
        SkillPreflightSpec(
            skill_id=SKILL_ID,
            decisions={"review": "maintenance-deferral-decision"},
            authority=SkillAuthorityContract(recommend=True, propose_decision=True),
        )
    )
    service = CEPIOApplicationService(runtime, skill_registry=skills)

    def external_review(invocation, host):
        evidence = host.read_object(invocation.subject.id)
        return SkillExecutionOutput(
            recommendation="Review the supported evidence; do not execute a work order.",
            evidence=invocation.evidence,
            outputs={"work_order_status": evidence.properties["status"]},
            decision_proposal=DecisionProposal(
                decision_type="maintenance-deferral-decision",
                subject=invocation.subject,
                problem="What does governed maintenance evidence justify?",
                observations=["Observed WorkOrder status: planned"],
                recommendation="Human maintenance review required",
            ),
        )

    service.register_skill_executor(SKILL_ID, external_review)
    return runtime, service


def _actor(role="ai_agent_recommender"):
    return FixedActorProvider(
        ActorContext(
            subject_id="foundry-agent-verified",
            roles={role},
            tenant_id="tenant-01",
            principal_type="agent",
            auth_mode="agentic-identity",
        )
    )


def _invocation():
    return SkillInvocation(
        skill_id=SKILL_ID,
        subject=ObjectRef(id="WO-EXT", type="WorkOrder"),
        evidence=[
            EvidenceReference(
                object_ref=ObjectRef(id="WO-EXT", type="WorkOrder"),
                role=EvidenceRole.supporting,
                provenance_ref="prov:synthetic-ext-01",
            )
        ],
    )


def test_external_gateway_injects_same_service_and_runtime_without_changing_default():
    runtime, service = _composed_service()
    provider = _actor()
    default_gateway = CEPIOMCPGateway(runtime, provider)
    gateway = CEPIOMCPGateway.with_application_service(service, provider)

    assert gateway.application_service is service
    assert gateway.runtime is service.runtime is runtime
    assert gateway.actor_provider is provider
    assert default_gateway.application_service is not service

    with pytest.raises(TypeError):
        CEPIOMCPGateway.with_application_service(object(), provider)


def test_composed_mcp_g1_admits_external_skill_and_persists_actor_scoped_decision():
    from mcp import Client

    runtime, service = _composed_service()
    server = build_mcp_server_with_application_service(service, _actor())

    async def check():
        async with Client(server, raise_exceptions=True) as client:
            available = {tool.name for tool in (await client.list_tools()).tools}
            assert available == {
                "cepio_get_object",
                "cepio_query_objects",
                "cepio_get_state_at",
                "cepio_explain_property",
                "cepio_call_function",
                "cepio_evaluate_skill",
            }
            result = await client.call_tool(
                "cepio_evaluate_skill",
                {"invocation": _invocation().model_dump(mode="json")},
            )
            assert result.is_error is False
            return result.structured_content

    response = asyncio.run(check())
    assert response["status"] == "completed"
    assert response["decision"]["created_by"] == "foundry-agent-verified"
    assert response["decision"]["subject"]["id"] == "WO-EXT"
    assert response["evidence"][0]["provenance_ref"] == "prov:synthetic-ext-01"
    assert response["outputs"]["work_order_status"] == "planned"
    assert runtime.get_object("WO-EXT").properties["status"] == "planned"


def test_composed_hosted_mcp_uses_g1_restriction_and_keeps_standard_full_surface():
    from mcp import Client

    runtime, service = _composed_service()
    hosted, app = build_hosted_mcp_with_application_service(service)
    assert hosted is not None
    assert app is not None
    full = build_mcp_server(runtime, _actor())

    async def check():
        async with Client(full) as client:
            available = {tool.name for tool in (await client.list_tools()).tools}
            assert "cepio_execute_action" in available
            assert "cepio_recommend_action" in available

    asyncio.run(check())
    with pytest.raises(ValueError, match="Unsupported"):
        build_mcp_server_with_application_service(service, _actor(), tool_profile="unknown")


def test_composed_service_preserves_actor_authority_and_failed_preflight():
    from mcp import Client

    _, service = _composed_service()
    server = build_mcp_server_with_application_service(service, _actor("autonomous_control_agent"))

    async def check():
        async with Client(server) as client:
            result = await client.call_tool(
                "cepio_evaluate_skill",
                {"invocation": _invocation().model_dump(mode="json")},
            )
            return result.structured_content

    response = asyncio.run(check())
    assert response["status"] == "blocked"
    assert response["decision"] is None

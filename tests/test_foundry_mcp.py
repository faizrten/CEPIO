from __future__ import annotations

import asyncio

import pytest

from cepio.bootstrap import build_runtime
from cepio.integrations.microsoft.foundry_gateway import (
    ActorContext,
    CEPIOMCPGateway,
    EntraClaimsMapper,
    FixedActorProvider,
)
from cepio.integrations.microsoft.foundry_mcp import build_mcp_server
from cepio.model import OntologyObject, PolicyEffect
from cepio.provenance import PropertyProvenance, SourceReference
from cepio.query import ObjectQuery, PropertyPredicate
from cepio.runtime import AuthorizationError


def _runtime():
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id="K-MCP",
            type="Compressor",
            name="MCP Compressor",
            properties={
                "criticality": "high",
                "operatingState": "degraded",
                "riskStatus": "elevated",
                "manufacturer": "Example OEM",
            },
            interfaces={"MaintainableAsset", "Inspectable", "RiskBearing"},
        )
    )
    runtime.upsert_object(
        OntologyObject(
            id="UNIT-MCP",
            type="ProcessUnit",
            name="MCP Process Unit",
            properties={"status": "online"},
        )
    )
    provenance = PropertyProvenance.create(
        object_id="K-MCP",
        property_name="asset:criticality",
        property_registry=runtime.property_registry,
        source=SourceReference(
            source_system="SAP",
            source_entity="Equipment",
            source_field="Criticality",
            source_record_id="K-MCP",
        ),
        mapping_kind="direct",
        mapping_version="1.0.0",
        source_value="high",
    )
    runtime.provenance_repository.append_property(provenance)
    return runtime


def _ai_actor() -> ActorContext:
    return ActorContext(
        subject_id="agent-foundry-01",
        roles={"ai_agent_recommender"},
        principal_type="agent",
        auth_mode="agentic-identity",
        tenant_id="tenant-01",
        client_id="agent-client-01",
    )


def test_gateway_filters_object_and_query_results_by_cepio_policy():
    runtime = _runtime()
    gateway = CEPIOMCPGateway(runtime, FixedActorProvider(_ai_actor()))

    obj = gateway.get_object("K-MCP")
    assert obj.properties["criticality"] == "high"
    assert "manufacturer" not in obj.properties

    result = gateway.query_objects(
        ObjectQuery(
            object_type="Equipment",
            predicates=[PropertyPredicate(property="criticality", operator="eq", value="high")],
        )
    )
    assert result.total == 1
    assert result.items[0].id == "K-MCP"
    assert "manufacturer" not in result.items[0].properties

    with pytest.raises(ValueError):
        gateway.query_objects(ObjectQuery())
    with pytest.raises(AuthorizationError):
        gateway.query_objects(ObjectQuery(object_type="ProcessUnit"))


def test_function_calls_are_explicitly_policy_authorized():
    runtime = _runtime()
    ai_gateway = CEPIOMCPGateway(runtime, FixedActorProvider(_ai_actor()))
    risk = ai_gateway.call_function("calculateAssetRisk", {"asset_id": "K-MCP"})
    assert isinstance(risk, float)

    blocked_actor = ActorContext(
        subject_id="autonomous-01",
        roles={"autonomous_control_agent"},
        principal_type="agent",
        auth_mode="agentic-identity",
    )
    blocked_gateway = CEPIOMCPGateway(runtime, FixedActorProvider(blocked_actor))
    with pytest.raises(AuthorizationError):
        blocked_gateway.call_function("calculateAssetRisk", {"asset_id": "K-MCP"})


def test_recommendation_and_execution_are_separate_permissions():
    runtime = _runtime()
    ai_gateway = CEPIOMCPGateway(runtime, FixedActorProvider(_ai_actor()))

    recommendation = ai_gateway.recommend_action(
        "CreateWorkOrder",
        "K-MCP",
        parameters={"title": "Inspect K-MCP"},
    )
    assert recommendation.policy.effect == PolicyEffect.recommend_only
    assert recommendation.recommendation_permitted is True
    assert recommendation.executable_by_current_actor is False

    with pytest.raises(AuthorizationError):
        ai_gateway.execute_action(
            "CreateWorkOrder",
            "K-MCP",
            parameters={"title": "Inspect K-MCP"},
        )

    engineer = ActorContext(
        subject_id="engineer-01",
        roles={"maintenance_engineer"},
        principal_type="user",
        auth_mode="oauth2",
    )
    engineer_gateway = CEPIOMCPGateway(runtime, FixedActorProvider(engineer))
    result = engineer_gateway.execute_action(
        "CreateWorkOrder",
        "K-MCP",
        parameters={"title": "Inspect K-MCP", "work_order_id": "WO-MCP-001"},
        idempotency_key="mcp-test-1",
    )
    assert result.status.value == "executed"
    assert runtime.get_object("WO-MCP-001").properties["createdBy"] == "engineer-01"


def test_entra_claims_mapper_maps_verified_claims_and_fails_closed():
    mapper = EntraClaimsMapper(
        role_map={"CEPIO.Agent.Recommender": "ai_agent_recommender"},
        group_role_map={"group-maint": "maintenance_engineer"},
    )
    actor = mapper.map_claims(
        {
            "oid": "principal-123",
            "tid": "tenant-123",
            "azp": "client-123",
            "roles": ["CEPIO.Agent.Recommender"],
            "groups": ["group-maint"],
        },
        principal_type="agent",
        auth_mode="agentic-identity",
    )
    assert actor.subject_id == "principal-123"
    assert actor.roles == {"ai_agent_recommender", "maintenance_engineer"}

    with pytest.raises(AuthorizationError):
        mapper.map_claims(
            {"oid": "principal-456", "roles": ["Unmapped.Role"]},
            principal_type="agent",
            auth_mode="agentic-identity",
        )


def test_actual_mcp_protocol_lists_governed_tools_and_hides_actor_arguments():
    from mcp import Client

    runtime = _runtime()
    server = build_mcp_server(runtime, FixedActorProvider(_ai_actor()))
    state_time = runtime.get_object("K-MCP").updated_at.isoformat()

    async def _exercise() -> None:
        async with Client(server, raise_exceptions=True) as client:
            listed = await client.list_tools()
            tools = {tool.name: tool for tool in listed.tools}
            assert set(tools) == {
                "cepio_get_object",
                "cepio_query_objects",
                "cepio_get_state_at",
                "cepio_explain_property",
                "cepio_call_function",
                "cepio_evaluate_skill",
                "cepio_recommend_action",
                "cepio_execute_action",
            }
            execute_schema = tools["cepio_execute_action"].input_schema
            assert "actor_id" not in execute_schema.get("properties", {})
            assert "actor_roles" not in execute_schema.get("properties", {})
            skill_schema = tools["cepio_evaluate_skill"].input_schema
            assert "actor_id" not in skill_schema.get("properties", {})
            assert "actor_roles" not in skill_schema.get("properties", {})

            obj_result = await client.call_tool("cepio_get_object", {"object_id": "K-MCP"})
            assert obj_result.is_error is False
            assert obj_result.structured_content["id"] == "K-MCP"
            assert "manufacturer" not in obj_result.structured_content["properties"]

            query_result = await client.call_tool(
                "cepio_query_objects",
                {
                    "query": {
                        "object_type": "Equipment",
                        "predicates": [
                            {"property": "criticality", "operator": "eq", "value": "high"}
                        ],
                    }
                },
            )
            assert query_result.is_error is False
            assert query_result.structured_content["total"] == 1
            assert query_result.structured_content["items"][0]["id"] == "K-MCP"

            state_result = await client.call_tool(
                "cepio_get_state_at",
                {"object_id": "K-MCP", "as_of_transaction": state_time},
            )
            assert state_result.is_error is False
            assert state_result.structured_content["id"] == "K-MCP"

            explain_result = await client.call_tool(
                "cepio_explain_property",
                {"object_id": "K-MCP", "property_name": "asset:criticality"},
            )
            assert explain_result.is_error is False
            assert explain_result.structured_content["object_id"] == "K-MCP"
            assert (
                explain_result.structured_content["provenance"][0]["source"]["source_system"]
                == "SAP"
            )

            rec_result = await client.call_tool(
                "cepio_recommend_action",
                {
                    "action_type": "CreateWorkOrder",
                    "target_id": "K-MCP",
                    "parameters": {"title": "Inspect via MCP"},
                },
            )
            assert rec_result.is_error is False
            assert rec_result.structured_content["policy"]["effect"] == "recommend_only"

    asyncio.run(_exercise())


def test_property_lineage_is_hidden_when_property_read_policy_denies_it():
    runtime = _runtime()
    gateway = CEPIOMCPGateway(runtime, FixedActorProvider(_ai_actor()))

    # A visible asset does not make all of its properties or their sources visible.
    with pytest.raises(AuthorizationError):
        gateway.explain_property("K-MCP", "manufacturer")

    explanation = gateway.explain_property("K-MCP", "asset:criticality")
    assert explanation["object_id"] == "K-MCP"
    assert explanation["provenance"][0]["source"]["source_system"] == "SAP"


def test_invalid_provenance_does_not_mutate_object_before_validation():
    runtime = _runtime()
    original = runtime.get_object("K-MCP").model_dump(mode="json")
    source = SourceReference(
        source_system="SAP",
        source_entity="Equipment",
        source_field="Criticality",
        source_record_id="K-MCP",
    )

    wrong_object = PropertyProvenance.create(
        object_id="UNRELATED-ASSET",
        property_name="asset:criticality",
        property_registry=runtime.property_registry,
        source=source,
        mapping_kind="direct",
        mapping_version="test-v1",
    )
    with pytest.raises(ValueError, match="object_id"):
        runtime.set_property("K-MCP", "asset:criticality", "low", provenance=wrong_object)
    assert runtime.get_object("K-MCP").model_dump(mode="json") == original

    wrong_property = PropertyProvenance.create(
        object_id="K-MCP",
        property_name="asset:conditionPercent",
        property_registry=runtime.property_registry,
        source=source,
        mapping_kind="direct",
        mapping_version="test-v1",
    )
    with pytest.raises(ValueError, match="IRI"):
        runtime.set_property("K-MCP", "asset:criticality", "low", provenance=wrong_property)
    assert runtime.get_object("K-MCP").model_dump(mode="json") == original

    runtime.provenance_repository = None
    with pytest.raises(RuntimeError, match="Provenance repository"):
        runtime.set_property("K-MCP", "asset:criticality", "low", provenance=wrong_object)
    assert runtime.get_object("K-MCP").model_dump(mode="json") == original


def test_valid_provenance_is_persisted_after_an_authorized_property_mutation():
    runtime = _runtime()
    record = PropertyProvenance.create(
        object_id="K-MCP",
        property_name="asset:criticality",
        property_registry=runtime.property_registry,
        source=SourceReference(
            source_system="SAP",
            source_entity="Equipment",
            source_field="Criticality",
            source_record_id="K-MCP",
        ),
        mapping_kind="direct",
        mapping_version="test-v2",
        source_value="low",
    )
    updated = runtime.set_property("K-MCP", "asset:criticality", "low", provenance=record)
    definition = runtime.property_registry.resolve("asset:criticality")
    assert updated.properties[definition.iri] == "low"
    explanation = runtime.explain_property("K-MCP", "asset:criticality")
    assert any(row["id"] == record.id for row in explanation["provenance"])
    assert any(row["mapping_version"] == "test-v2" for row in explanation["provenance"])

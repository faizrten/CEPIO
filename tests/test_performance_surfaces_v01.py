from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cepio.auth import ActorContext, get_actor_context
from cepio.config import RuntimeSettings
from cepio.mcp import MCPFacade
from cepio.performance_api import build_performance_router
from cepio.performance_contract import (
    PerformanceContract,
    PerformanceNode,
    PerformanceResponseBinding,
    PerformanceSubject,
    PerformanceTarget,
)
from cepio.performance_registry import (
    InMemoryPerformanceContractStore,
    PerformanceContractRegistry,
    SQLitePerformanceContractStore,
)
from cepio.performance_runtime import PerformanceObservation, PerformanceStatus
from cepio.performance_service import PerformanceService, build_performance_service
from cepio.runtime import AuthorizationError


NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)


def performance_contract(
    *,
    contract_id: str = "org-a-performance",
    version: str = "1.0.0",
    organization_id: str | None = "org-a",
) -> PerformanceContract:
    layer = "industry_reference" if organization_id is None else "organization"
    subject_id = organization_id or "industry"
    return PerformanceContract(
        id=contract_id,
        version=version,
        name="Availability performance",
        layer=layer,
        organization_id=organization_id,
        subjects=(
            PerformanceSubject(
                id=subject_id,
                kind="enterprise",
                name="Industry" if organization_id is None else "Org A",
            ),
        ),
        nodes=(
            PerformanceNode(
                id="availability",
                kind="kpi",
                name="Operational availability",
                scope_subject_id=subject_id,
                unit="ratio",
                target=PerformanceTarget(operator="gte", value=0.95),
            ),
            PerformanceNode(
                id="healthy-cost",
                kind="guardrail",
                name="Healthy cost guardrail",
                scope_subject_id=subject_id,
                target=PerformanceTarget(operator="lte", value=100.0),
            ),
        ),
        response_bindings=(
            PerformanceResponseBinding(
                id="availability-response",
                node_id="availability",
                statuses=frozenset({"off_track", "critical"}),
                workflow_definition_id="investigate-availability-loss",
                rationale="Investigate material availability deviation",
            ),
        ),
    )


def service_with_active_contract(
    *, organization_id: str | None = "org-a", contract_id: str = "org-a-performance"
) -> PerformanceService:
    registry = PerformanceContractRegistry(InMemoryPerformanceContractStore())
    registry.register(
        performance_contract(contract_id=contract_id, organization_id=organization_id),
        activate=True,
        created_at=NOW,
    )
    return PerformanceService(registry)


def observations() -> tuple[PerformanceObservation, ...]:
    return (
        PerformanceObservation(
            node_id="availability",
            value=0.90,
            observed_at=NOW,
            evidence_refs=("pi://availability/2026-10-19",),
        ),
        PerformanceObservation(
            node_id="healthy-cost",
            value=80.0,
            observed_at=NOW,
            evidence_refs=("erp://cost/2026-10-19",),
        ),
    )


def test_service_returns_explainable_deviation_and_recommend_only_candidate():
    service = service_with_active_contract()

    assessment = service.evaluate("org-a-performance", observations(), evaluated_at=NOW)

    assert assessment.contract_version == "1.0.0"
    assert assessment.organization_id == "org-a"
    assert len(assessment.source_revision_hashes) == 1
    assert len(assessment.deviations) == 1
    deviation = assessment.deviations[0]
    assert deviation.node_id == "availability"
    assert deviation.status == PerformanceStatus.off_track
    assert deviation.evidence_refs == ("pi://availability/2026-10-19",)
    assert assessment.evaluation.node("healthy-cost").status == PerformanceStatus.on_track
    assert deviation.workflow_candidates[0].workflow_definition_id == (
        "investigate-availability-loss"
    )
    assert assessment.workflow_candidates[0].authority == "recommend_only"
    assert assessment.workflow_candidates[0].policy_required is True
    assert assessment.authority == "recommend_only"
    assert assessment.policy_required is True


def test_service_resolve_exposes_pinned_revision_provenance():
    service = service_with_active_contract()

    resolution = service.resolve("org-a-performance")

    assert resolution.resolved.contract.version == "1.0.0"
    assert len(resolution.source_revisions) == 1
    assert resolution.source_revisions[0].definition_hash


def test_build_performance_service_uses_memory_store():
    settings = RuntimeSettings(
        environment="test",
        db_url="memory://",
        resource_root=None,
        ontology_dir=None,
        profiles=(),
        validate_types=True,
        validate_properties=True,
        strict_properties=False,
    )

    service = build_performance_service(settings)

    assert isinstance(service.registry.store, InMemoryPerformanceContractStore)


def test_build_performance_service_uses_sqlite_store(tmp_path):
    db_path = tmp_path / "cepio.db"
    settings = RuntimeSettings(
        environment="test",
        db_url=f"sqlite:///{db_path}",
        resource_root=None,
        ontology_dir=None,
        profiles=(),
        validate_types=True,
        validate_properties=True,
        strict_properties=False,
    )

    service = build_performance_service(settings)

    assert isinstance(service.registry.store, SQLitePerformanceContractStore)
    service.registry.store.close()


def rest_client(
    service: PerformanceService, *, tenant_id: str | None = "org-a"
) -> TestClient:
    app = FastAPI()
    app.include_router(build_performance_router(service))
    app.dependency_overrides[get_actor_context] = lambda: ActorContext(
        actor_id="user-1",
        roles={"performance_reader"},
        tenant_id=tenant_id,
    )
    return TestClient(app)


def test_experimental_rest_resolves_and_evaluates_matching_tenant():
    service = service_with_active_contract()
    client = rest_client(service)

    resolved = client.get(
        "/experimental/performance/v0.1/contracts/org-a-performance/resolved"
    )
    evaluated = client.post(
        "/experimental/performance/v0.1/contracts/org-a-performance/evaluate",
        json={
            "evaluated_at": NOW.isoformat(),
            "observations": [item.model_dump(mode="json") for item in observations()],
        },
    )

    assert resolved.status_code == 200
    assert resolved.json()["resolved"]["contract"]["organization_id"] == "org-a"
    assert evaluated.status_code == 200
    body = evaluated.json()
    assert body["deviations"][0]["node_id"] == "availability"
    assert body["workflow_candidates"][0]["authority"] == "recommend_only"


def test_experimental_rest_fails_closed_across_tenant_boundary():
    service = service_with_active_contract()
    client = rest_client(service, tenant_id="org-b")

    resolved = client.get(
        "/experimental/performance/v0.1/contracts/org-a-performance/resolved"
    )
    evaluated = client.post(
        "/experimental/performance/v0.1/contracts/org-a-performance/evaluate",
        json={
            "evaluated_at": NOW.isoformat(),
            "observations": [item.model_dump(mode="json") for item in observations()],
        },
    )

    assert resolved.status_code == 403
    assert evaluated.status_code == 403
    assert resolved.json()["detail"]["code"] == "performance_organization_scope"


def test_experimental_rest_allows_tenant_neutral_industry_reference():
    service = service_with_active_contract(
        organization_id=None, contract_id="industry-performance"
    )
    client = rest_client(service, tenant_id="org-b")

    response = client.get(
        "/experimental/performance/v0.1/contracts/industry-performance/resolved"
    )

    assert response.status_code == 200
    assert response.json()["resolved"]["contract"]["organization_id"] is None


def test_experimental_rest_maps_missing_and_invalid_evaluation_errors():
    service = service_with_active_contract()
    client = rest_client(service)

    missing = client.get(
        "/experimental/performance/v0.1/contracts/missing/resolved"
    )
    invalid = client.post(
        "/experimental/performance/v0.1/contracts/org-a-performance/evaluate",
        json={
            "evaluated_at": "2026-10-19T12:00:00",
            "observations": [item.model_dump(mode="json") for item in observations()],
        },
    )

    assert missing.status_code == 404
    assert missing.json()["detail"]["code"] == "ACTIVE_REVISION_NOT_FOUND"
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["code"] == "performance_evaluation"


def test_experimental_rest_routes_do_not_enter_openapi_schema():
    service = service_with_active_contract()
    client = rest_client(service)

    schema = client.get("/openapi.json").json()

    assert not any(path.startswith("/experimental/performance") for path in schema["paths"])


class DummyRuntime:
    pass


def test_mcp_performance_tools_are_opt_in_and_tenant_scoped():
    service = service_with_active_contract()
    plain = MCPFacade(DummyRuntime(), actor_id="agent", actor_roles=set())  # type: ignore[arg-type]
    scoped = MCPFacade(
        DummyRuntime(),  # type: ignore[arg-type]
        actor_id="agent",
        actor_roles={"ai_agent_recommender"},
        tenant_id="org-a",
        performance_service=service,
    )

    assert "cepio_evaluate_performance" not in {
        item["name"] for item in plain.list_tools()
    }
    names = {item["name"] for item in scoped.list_tools()}
    assert "cepio_resolve_performance_contract" in names
    assert "cepio_evaluate_performance" in names

    resolved = scoped.call_tool(
        "cepio_resolve_performance_contract", {"contract_id": "org-a-performance"}
    )
    evaluated = scoped.call_tool(
        "cepio_evaluate_performance",
        {
            "contract_id": "org-a-performance",
            "evaluated_at": NOW.isoformat(),
            "observations": [item.model_dump(mode="json") for item in observations()],
        },
    )

    assert resolved["resolved"]["contract"]["organization_id"] == "org-a"
    assert evaluated["deviations"][0]["status"] == "off_track"
    assert evaluated["workflow_candidates"][0]["policy_required"] is True


def test_mcp_performance_tools_fail_closed_for_cross_tenant_and_unconfigured_service():
    service = service_with_active_contract()
    wrong_tenant = MCPFacade(
        DummyRuntime(),  # type: ignore[arg-type]
        actor_id="agent",
        actor_roles=set(),
        tenant_id="org-b",
        performance_service=service,
    )
    plain = MCPFacade(DummyRuntime(), actor_id="agent", actor_roles=set())  # type: ignore[arg-type]

    with pytest.raises(AuthorizationError):
        wrong_tenant.call_tool(
            "cepio_resolve_performance_contract",
            {"contract_id": "org-a-performance"},
        )
    with pytest.raises(AuthorizationError):
        wrong_tenant.call_tool(
            "cepio_evaluate_performance",
            {"contract_id": "org-a-performance", "observations": []},
        )
    with pytest.raises(KeyError, match="performance service is not configured"):
        plain.call_tool(
            "cepio_resolve_performance_contract",
            {"contract_id": "org-a-performance"},
        )
    with pytest.raises(KeyError, match="performance service is not configured"):
        plain.call_tool(
            "cepio_evaluate_performance",
            {"contract_id": "org-a-performance", "observations": []},
        )


def test_mcp_tenant_neutral_performance_contract_is_accessible():
    service = service_with_active_contract(
        organization_id=None, contract_id="industry-performance"
    )
    facade = MCPFacade(
        DummyRuntime(),  # type: ignore[arg-type]
        actor_id="agent",
        actor_roles=set(),
        tenant_id=None,
        performance_service=service,
    )

    result = facade.call_tool(
        "cepio_resolve_performance_contract",
        {"contract_id": "industry-performance"},
    )

    assert result["resolved"]["contract"]["organization_id"] is None

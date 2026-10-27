"""Rig 07 headless executive preview integration and security tests."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from cepio.application_contract import CEPIOApplicationService, ExecutionContext
from cepio.auth import ActorContext, get_actor_context
from cepio.bootstrap import build_runtime
from cepio.industry_iq import install_industry_iq_packs
from cepio.industry_performance_packs import drilling_contractor_performance_pack
from cepio.model import ObjectRef, OntologyObject
from cepio.performance_contract import PerformanceStatus
from cepio.performance_executive import (
    ExecutivePackageRequest,
    ExecutivePerformanceError,
    ExecutivePerformanceService,
)
from cepio.performance_executive_api import build_performance_executive_router
from cepio.performance_industry_iq import (
    PERFORMANCE_RESPONSE_IQ_PACK,
    PerformanceIndustryIQService,
    PerformanceReasoningError,
    PerformanceReasoningRequest,
)
from cepio.performance_registry import InMemoryPerformanceContractStore, PerformanceContractRegistry
from cepio.performance_runtime import PerformanceObservation
from cepio.performance_service import PerformanceService
from scripts.drilling_performance_activation_v01 import (
    CONTRACT_ID,
    EVALUATED_AT,
    KR,
    LEAKAGE,
    NPT,
    ORG,
    SAFETY,
    UPTIME,
    organization_overlay,
    run_activation,
)

RIG = "rig-07"


def _fixture(*, financial: bool = True, safety: bool = True):
    activation = run_activation(
        include_financial_evidence=financial,
        include_guardrail_evidence=safety,
    )
    runtime = build_runtime()
    runtime.upsert_object(
        OntologyObject(
            id=RIG,
            type="Equipment",
            name="SYNTHETIC Rig 07",
            properties={"sharingScope": "internal"},
        )
    )
    install_industry_iq_packs(runtime, [PERFORMANCE_RESPONSE_IQ_PACK])
    registry = PerformanceContractRegistry(InMemoryPerformanceContractStore())
    registry.register(
        drilling_contractor_performance_pack(), activate=True, created_at=EVALUATED_AT
    )
    registry.register(organization_overlay(), activate=True, created_at=EVALUATED_AT)
    service = ExecutivePerformanceService(
        PerformanceIndustryIQService(PerformanceService(registry), CEPIOApplicationService(runtime))
    )
    # This subject binding is ONLY a controlled synthetic fixture. Production
    # evidence-to-object linkage must originate in an authorized data binding.
    observations = tuple(
        PerformanceObservation(
            node_id=node.node_id,
            value=node.value,
            observed_at=node.observed_at,
            evidence_refs=node.evidence_refs,
            source_subject_id=RIG if node.node_id == NPT else None,
        )
        for node in activation.assessment.evaluation.nodes
        if node.value is not None
        and node.observed_at is not None
        and node.evidence_refs
        and node.status != PerformanceStatus.unknown
    )
    request = ExecutivePackageRequest(
        reasoning=PerformanceReasoningRequest(
            contract_id=CONTRACT_ID,
            node_id=NPT,
            subject=ObjectRef(id=RIG, type="Equipment"),
            observations=observations,
            evaluated_at=EVALUATED_AT,
        ),
        financial_node_id=LEAKAGE,
    )
    context = ExecutionContext(
        actor_id="synthetic-rigco-ceo",
        actor_roles=frozenset({"cepio_admin"}),
        tenant_id=ORG,
        correlation_id="synthetic-ceo-investigation-01",
    )
    return runtime, service, request, context


def test_rig07_executive_preview_reuses_iq_and_preserves_all_five_boundaries():
    runtime, service, request, context = _fixture()
    package = service.preview(request, context)
    nodes = {node.node_id: node for node in package.performance}

    assert package.organization_id == ORG
    assert package.contract_id == CONTRACT_ID
    assert package.contract_version == "0.1.0"
    assert len(package.source_revision_hashes) == 2
    assert package.focus_node_id == NPT
    assert package.subject == ObjectRef(id=RIG, type="Equipment")
    assert nodes[NPT].value == pytest.approx(0.10)
    assert nodes[NPT].status == PerformanceStatus.off_track
    assert nodes[KR].status == PerformanceStatus.off_track
    assert nodes[UPTIME].value == pytest.approx(0.90)
    assert nodes[SAFETY].status == PerformanceStatus.on_track
    assert any(person.relation == "accountable_for" for person in nodes[UPTIME].accountabilities)
    assert package.financial_status == "observed_unverified"
    assert package.financial_observation is not None
    assert package.financial_observation.value == pytest.approx(32000.0)
    assert (
        package.financial_observation.interpretation == "caller_supplied_unverified_currency_metric"
    )
    assert package.decision_proposal.recommended_action is None
    assert package.decision_proposal.confidence is None
    assert package.workflow_candidates[0].authority == "recommend_only"
    assert package.evidence_status == "caller_supplied_unverified"
    assert package.authority == "recommend_only"
    assert package.policy_required is True
    assert package.decision_persisted is False
    assert package.workflow_started is False
    assert package.action_executed is False
    assert package.causal_claim_made is False
    assert runtime.all_audits() == []


def test_missing_commercial_evidence_never_creates_financial_claim():
    _, service, request, context = _fixture(financial=False)
    package = service.preview(request, context)
    assert package.financial_observation is None
    assert package.financial_status == "evidence_missing"
    assert next(node for node in package.performance if node.node_id == LEAKAGE).status == (
        PerformanceStatus.unknown
    )


def test_missing_safety_evidence_remains_unknown_not_safe():
    _, service, request, context = _fixture(safety=False)
    package = service.preview(request, context)
    assert next(node for node in package.performance if node.node_id == SAFETY).status == (
        PerformanceStatus.unknown
    )


def test_wrong_tenant_and_unbound_source_are_rejected():
    _, service, request, context = _fixture()
    with pytest.raises(PerformanceReasoningError) as error:
        service.preview(
            request,
            context.model_copy(update={"tenant_id": "another-customer"}),
        )
    assert error.value.code == "ORGANIZATION_SCOPE_MISMATCH"

    mismatched = request.model_copy(
        update={
            "reasoning": request.reasoning.model_copy(
                update={"subject": ObjectRef(id="other-rig", type="Equipment")}
            )
        }
    )
    with pytest.raises(PerformanceReasoningError) as error:
        service.preview(mismatched, context)
    assert error.value.code == "SOURCE_SUBJECT_MISMATCH"


def test_missing_direct_npt_evidence_cannot_create_decision_proposal():
    _, service, request, context = _fixture()
    obs = tuple(item for item in request.reasoning.observations if item.node_id != NPT)
    revised = request.model_copy(
        update={"reasoning": request.reasoning.model_copy(update={"observations": obs})}
    )
    with pytest.raises(PerformanceReasoningError) as error:
        service.preview(revised, context)
    assert error.value.code in {"NODE_NOT_ACTIONABLE", "SOURCE_SUBJECT_REQUIRED"}


def test_non_financial_metric_cannot_be_labeled_financial():
    _, service, request, context = _fixture()
    with pytest.raises(ExecutivePerformanceError) as error:
        service.preview(request.model_copy(update={"financial_node_id": NPT}), context)
    assert error.value.code == "INVALID_FINANCIAL_NODE"


def _client(tenant: str = ORG):
    _, service, request, _ = _fixture()
    app = FastAPI()
    app.include_router(build_performance_executive_router(service))
    app.dependency_overrides[get_actor_context] = lambda: ActorContext(
        actor_id="synthetic-ceo",
        roles={"cepio_admin"},
        tenant_id=tenant,
    )
    return TestClient(app), request


def test_rest_preview_exposes_read_only_schema_without_actor_in_body():
    client, request = _client()
    response = client.post(
        "/experimental/performance/v0.1/executive/preview",
        json=request.model_dump(mode="json"),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["authority"] == "recommend_only"
    assert body["decision_persisted"] is False
    assert body["financial_status"] == "observed_unverified"
    assert body["decision_proposal"]["recommended_action"] is None
    assert (
        "/experimental/performance/v0.1/executive/preview"
        not in client.get("/openapi.json").json()["paths"]
    )


def test_rest_preview_requires_admin_role_and_explicit_evaluation_time():
    client, request = _client()
    client.app.dependency_overrides[get_actor_context] = lambda: ActorContext(
        actor_id="synthetic-readonly",
        roles={"performance_reader"},
        tenant_id=ORG,
    )
    response = client.post(
        "/experimental/performance/v0.1/executive/preview",
        json=request.model_dump(mode="json"),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "executive_preview_admin_required"

    _, service, request, context = _fixture()
    missing_time = request.model_copy(
        update={"reasoning": request.reasoning.model_copy(update={"evaluated_at": None})}
    )
    with pytest.raises(ExecutivePerformanceError) as error:
        service.preview(missing_time, context)
    assert error.value.code == "EVALUATION_TIME_REQUIRED"


def test_rest_preview_denies_cross_tenant_and_simulation_false():
    client, request = _client(tenant="different-tenant")
    response = client.post(
        "/experimental/performance/v0.1/executive/preview",
        json=request.model_dump(mode="json"),
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "ORGANIZATION_SCOPE_MISMATCH"

    client, request = _client()
    payload = request.model_dump(mode="json")
    payload["simulation_only"] = False
    response = client.post("/experimental/performance/v0.1/executive/preview", json=payload)
    assert response.status_code == 422

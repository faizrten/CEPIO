from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import BaseModel

from cepio.auth import ActorContext
from cepio.bootstrap import build_runtime
from cepio.performance_business_logic import (
    BusinessLogicDefinition,
    BusinessLogicInput,
    BusinessLogicInvocation,
    BusinessLogicRegistry,
)
from cepio.performance_contract import (
    PerformanceContract,
    PerformanceNode,
    PerformanceSubject,
    PerformanceTarget,
)
from cepio.performance_registry import PerformanceContractRegistry, SQLitePerformanceContractStore
from cepio.performance_runtime import PerformanceObservation
from cepio.performance_service import (
    PerformanceAccessPolicy,
    PerformanceEvaluationRequest,
    PerformanceService,
    PerformanceServiceError,
    build_performance_service,
)

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)


class AvailabilityInputs(BaseModel):
    uptime_hours: float
    total_hours: float


def performance_contract(version: str = "1.0.0") -> PerformanceContract:
    return PerformanceContract(
        id="refinery-performance",
        version=version,
        name=f"Refinery Performance {version}",
        layer="organization",
        organization_id="refinery-co",
        subjects=(
            PerformanceSubject(id="refinery-co", kind="enterprise", name="Refinery Co"),
        ),
        nodes=(
            PerformanceNode(
                id="availability",
                kind="kpi",
                name="Operational Availability",
                scope_subject_id="refinery-co",
                formula_ref="logic://refinery-co/availability/v7",
                unit="ratio",
                max_observation_age_seconds=3600,
                target=PerformanceTarget(operator="gte", value=0.95),
            ),
        ),
    )


def make_service(*, tenant_map=None, with_logic=True):
    runtime = build_runtime()
    runtime.register_function(
        "calculateAvailability",
        lambda runtime, uptime_hours, total_hours: uptime_hours / total_hours,
        input_model=AvailabilityInputs,
        output_type=float,
    )
    registry = PerformanceContractRegistry()
    registry.register(performance_contract(), activate=True, created_at=NOW)
    logic_registry = BusinessLogicRegistry()
    if with_logic:
        logic_registry.register(
            BusinessLogicDefinition(
                formula_ref="logic://refinery-co/availability/v7",
                name="Availability v7",
                function_name="calculateAvailability",
                input_names=("uptime_hours", "total_hours"),
                organization_id="refinery-co",
                output_unit="ratio",
                max_input_age_seconds=3600,
            )
        )
    service = PerformanceService(
        runtime,
        registry,
        access_policy=PerformanceAccessPolicy(
            tenant_map if tenant_map is not None else {"tenant-a": {"refinery-co"}}
        ),
        business_logic_registry=logic_registry,
    )
    return runtime, service


def actor(*, roles=None, tenant_id="tenant-a"):
    return ActorContext(
        actor_id="actor-1",
        roles=roles or {"cepio_admin"},
        tenant_id=tenant_id,
    )


def invocation(observed_at=NOW):
    return BusinessLogicInvocation(
        node_id="availability",
        inputs=(
            BusinessLogicInput(
                name="uptime_hours",
                value=96.0,
                observed_at=observed_at,
                evidence_refs=("pi:uptime",),
            ),
            BusinessLogicInput(
                name="total_hours",
                value=100.0,
                observed_at=observed_at,
                evidence_refs=("pi:total",),
            ),
        ),
    )


def assert_error(code, callback, *, status_code=None):
    with pytest.raises(PerformanceServiceError) as exc:
        callback()
    assert exc.value.code == code
    if status_code is not None:
        assert exc.value.status_code == status_code


def test_resolve_and_evaluate_formula_through_shared_service():
    _, service = make_service()
    view = service.resolve(actor(), "refinery-co", "refinery-performance")
    assert view.contract.organization_id == "refinery-co"
    assert view.contract.version == "1.0.0"
    assert [item.contract_id for item in view.source_revisions] == ["refinery-performance"]

    result = service.evaluate(
        actor(),
        "refinery-co",
        "refinery-performance",
        PerformanceEvaluationRequest(
            business_logic=(invocation(NOW - timedelta(minutes=5)),),
            evaluated_at=NOW,
        ),
    )
    assert result.contract_id == "refinery-performance"
    assert result.business_logic_executions[0].value == 0.96
    assert result.evaluation.node("availability").status.value == "on_track"
    assert result.evaluation.workflow_candidates == ()


def test_direct_observations_use_existing_node_freshness_policy():
    _, service = make_service()
    result = service.evaluate(
        actor(),
        "refinery-co",
        "refinery-performance",
        PerformanceEvaluationRequest(
            observations=(
                PerformanceObservation(
                    node_id="availability",
                    value=0.96,
                    observed_at=NOW - timedelta(hours=2),
                    evidence_refs=("historian:availability",),
                ),
            ),
            evaluated_at=NOW,
        ),
    )
    node = result.evaluation.node("availability")
    assert node.status.value == "unknown"
    assert node.reasons == ("Observation is stale for this performance node",)


def test_customer_scope_is_explicit_and_fail_closed():
    _, service = make_service()
    assert_error(
        "PERFORMANCE_TENANT_REQUIRED",
        lambda: service.resolve(actor(tenant_id=None), "refinery-co", "refinery-performance"),
        status_code=403,
    )
    assert_error(
        "PERFORMANCE_ORGANIZATION_FORBIDDEN",
        lambda: service.resolve(actor(), "other-refinery", "refinery-performance"),
        status_code=403,
    )
    _, unmapped = make_service(tenant_map={})
    assert_error(
        "PERFORMANCE_ORGANIZATION_FORBIDDEN",
        lambda: unmapped.resolve(actor(), "refinery-co", "refinery-performance"),
        status_code=403,
    )


def test_existing_kpi_read_policy_and_function_policy_remain_authoritative():
    _, service = make_service()
    assert_error(
        "PERFORMANCE_READ_FORBIDDEN",
        lambda: service.resolve(
            actor(roles={"petrophysicist"}), "refinery-co", "refinery-performance"
        ),
        status_code=403,
    )
    assert service.resolve(
        actor(roles={"auditor"}), "refinery-co", "refinery-performance"
    )
    assert_error(
        "PERFORMANCE_FUNCTION_FORBIDDEN",
        lambda: service.evaluate(
            actor(roles={"auditor"}),
            "refinery-co",
            "refinery-performance",
            PerformanceEvaluationRequest(business_logic=(invocation(),), evaluated_at=NOW),
        ),
        status_code=403,
    )


def test_service_rejects_ambiguous_observation_source_and_invalid_evidence():
    _, service = make_service()
    direct = PerformanceObservation(
        node_id="availability",
        value=0.97,
        observed_at=NOW,
        evidence_refs=("manual:availability",),
    )
    assert_error(
        "PERFORMANCE_OBSERVATION_SOURCE_CONFLICT",
        lambda: service.evaluate(
            actor(),
            "refinery-co",
            "refinery-performance",
            PerformanceEvaluationRequest(
                observations=(direct,),
                business_logic=(invocation(),),
                evaluated_at=NOW,
            ),
        ),
    )
    naive = direct.model_copy(update={"observed_at": NOW.replace(tzinfo=None)})
    assert_error(
        "PERFORMANCE_EVALUATION_INVALID",
        lambda: service.evaluate(
            actor(),
            "refinery-co",
            "refinery-performance",
            PerformanceEvaluationRequest(observations=(naive,), evaluated_at=NOW),
        ),
    )


def test_service_translates_registry_and_business_logic_errors():
    _, service = make_service(with_logic=False)
    assert_error(
        "ACTIVE_REVISION_NOT_FOUND",
        lambda: service.resolve(actor(), "refinery-co", "missing-contract"),
        status_code=404,
    )
    assert_error(
        "FORMULA_NOT_FOUND",
        lambda: service.evaluate(
            actor(),
            "refinery-co",
            "refinery-performance",
            PerformanceEvaluationRequest(business_logic=(invocation(),), evaluated_at=NOW),
        ),
    )


def test_access_policy_environment_validation(monkeypatch):
    monkeypatch.setenv(
        "CEPIO_TENANT_ORGANIZATION_MAP",
        '{"tenant-a": ["refinery-co", "petchem-co"]}',
    )
    policy = PerformanceAccessPolicy.from_env()
    policy.require_organization(actor(), "refinery-co")

    monkeypatch.setenv("CEPIO_TENANT_ORGANIZATION_MAP", "not-json")
    with pytest.raises(RuntimeError, match="valid JSON"):
        PerformanceAccessPolicy.from_env()

    monkeypatch.setenv("CEPIO_TENANT_ORGANIZATION_MAP", "[]")
    with pytest.raises(RuntimeError, match="JSON object"):
        PerformanceAccessPolicy.from_env()

    monkeypatch.setenv("CEPIO_TENANT_ORGANIZATION_MAP", '{"tenant-a": "refinery-co"}')
    with pytest.raises(RuntimeError, match="arrays of non-empty strings"):
        PerformanceAccessPolicy.from_env()

    monkeypatch.setenv("CEPIO_TENANT_ORGANIZATION_MAP", '{"tenant-a": [""]}')
    with pytest.raises(RuntimeError, match="arrays of non-empty strings"):
        PerformanceAccessPolicy.from_env()


def test_builder_uses_sqlite_registry_when_configured(monkeypatch, tmp_path):
    runtime = build_runtime()
    database = tmp_path / "performance.db"
    monkeypatch.setenv("CEPIO_PERFORMANCE_REGISTRY_PATH", str(database))
    monkeypatch.setenv("CEPIO_TENANT_ORGANIZATION_MAP", '{"tenant-a": ["refinery-co"]}')
    service = build_performance_service(runtime)
    assert isinstance(service.registry.store, SQLitePerformanceContractStore)
    service.registry.store.close()


def test_builder_defaults_to_in_memory_registry(monkeypatch):
    runtime = build_runtime()
    monkeypatch.delenv("CEPIO_PERFORMANCE_REGISTRY_PATH", raising=False)
    monkeypatch.delenv("CEPIO_TENANT_ORGANIZATION_MAP", raising=False)
    service = build_performance_service(runtime)
    assert service.access_policy.tenant_organizations == {}
    assert service.registry.list_versions("missing") == ()

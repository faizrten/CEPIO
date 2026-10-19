from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import BaseModel, ValidationError

from cepio.performance_business_logic import (
    BusinessLogicDefinition,
    BusinessLogicExecutionError,
    BusinessLogicInput,
    BusinessLogicInvocation,
    BusinessLogicRegistry,
    PerformanceBusinessLogicRuntime,
)
from cepio.performance_contract import (
    PerformanceContract,
    PerformanceNode,
    PerformanceSubject,
    PerformanceTarget,
)
from cepio.performance_runtime import PerformanceRuntime
from cepio.runtime import CEPIORuntime

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)


class AvailabilityInputs(BaseModel):
    uptime_hours: float
    total_hours: float


class StructuredOutput(BaseModel):
    metrics: dict[str, float]


def contract(*, formula_ref: str | None = "logic://refinery-co/availability/v7", unit="ratio"):
    return PerformanceContract(
        id="refinery-co-performance",
        version="1.0.0",
        name="Refinery Co Performance",
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
                formula_ref=formula_ref,
                unit=unit,
                target=PerformanceTarget(operator="gte", value=0.95),
            ),
        ),
    )


def definition(**overrides):
    values = {
        "formula_ref": "logic://refinery-co/availability/v7",
        "name": "Operational availability v7",
        "function_name": "calculateAvailability",
        "input_names": ("uptime_hours", "total_hours"),
        "organization_id": "refinery-co",
        "output_path": "metrics.availability",
        "output_unit": "ratio",
        "max_input_age_seconds": 3600,
    }
    values.update(overrides)
    return BusinessLogicDefinition(**values)


def inputs(*, uptime_time=NOW, total_time=NOW):
    return (
        BusinessLogicInput(
            name="uptime_hours",
            value=96.0,
            observed_at=uptime_time,
            evidence_refs=("pi:uptime", "batch:2026-10-19"),
        ),
        BusinessLogicInput(
            name="total_hours",
            value=100.0,
            observed_at=total_time,
            evidence_refs=("pi:total", "batch:2026-10-19"),
        ),
    )


def runtime_with_function(*, handler=None):
    runtime = CEPIORuntime()
    runtime.register_function(
        "calculateAvailability",
        handler
        or (
            lambda runtime, uptime_hours, total_hours: StructuredOutput(
                metrics={"availability": uptime_hours / total_hours}
            )
        ),
        input_model=AvailabilityInputs,
        output_type=StructuredOutput,
    )
    return runtime


def business_logic_runtime(*, logic=None, function_runtime=None):
    registry = BusinessLogicRegistry()
    registry.register(logic or definition())
    return PerformanceBusinessLogicRuntime(function_runtime or runtime_with_function(), registry)


def assert_error(code, callback):
    with pytest.raises(BusinessLogicExecutionError) as exc:
        callback()
    assert exc.value.code == code


def test_materializes_existing_performance_observation_and_evaluates_on_track():
    logic_runtime = business_logic_runtime()
    materialized = logic_runtime.materialize(
        contract(),
        "availability",
        inputs(
            uptime_time=NOW - timedelta(minutes=10),
            total_time=NOW - timedelta(minutes=20),
        ),
        evaluated_at=NOW,
    )

    assert materialized.observation.value == 0.96
    assert materialized.observation.observed_at == NOW - timedelta(minutes=20)
    assert materialized.observation.evidence_refs == (
        "batch:2026-10-19",
        "pi:total",
        "pi:uptime",
    )
    assert materialized.execution.formula_ref == "logic://refinery-co/availability/v7"
    assert materialized.execution.definition_hash
    assert materialized.execution.function_name == "calculateAvailability"
    assert materialized.execution.organization_id == "refinery-co"
    assert materialized.execution.value == 0.96
    assert materialized.execution.unit == "ratio"
    assert [item.name for item in materialized.execution.inputs] == [
        "total_hours",
        "uptime_hours",
    ]
    assert all(not hasattr(item, "value") for item in materialized.execution.inputs)

    evaluation = PerformanceRuntime().evaluate(
        contract(), [materialized.observation], evaluated_at=NOW
    )
    assert evaluation.node("availability").status.value == "on_track"


def test_industry_neutral_logic_can_materialize_organization_contract_and_direct_numeric_output():
    logic = definition(
        organization_id=None,
        output_path=None,
        output_unit=None,
        max_input_age_seconds=None,
    )
    function_runtime = CEPIORuntime()
    function_runtime.register_function(
        "calculateAvailability",
        lambda runtime, uptime_hours, total_hours: uptime_hours / total_hours,
        input_model=AvailabilityInputs,
        output_type=float,
    )
    result = business_logic_runtime(logic=logic, function_runtime=function_runtime).materialize(
        contract(), "availability", inputs(), evaluated_at=NOW
    )
    assert result.observation.value == 0.96
    assert result.execution.organization_id is None
    assert result.execution.unit is None


def test_registry_is_immutable_by_exact_formula_reference():
    registry = BusinessLogicRegistry()
    registered = registry.register(definition())
    assert registry.get(registered.definition.formula_ref) == registered
    assert_error("FORMULA_ALREADY_REGISTERED", lambda: registry.register(definition()))
    assert_error("FORMULA_NOT_FOUND", lambda: registry.get("logic://missing/v1"))


@pytest.mark.parametrize(
    "overrides",
    [
        {"formula_ref": ""},
        {"function_name": ""},
        {"input_names": ("x", "x")},
        {"input_names": ("x", "")},
        {"output_path": "metrics..availability"},
    ],
)
def test_definition_validation_is_fail_closed(overrides):
    with pytest.raises(ValidationError):
        definition(**overrides)


def test_materialization_rejects_naive_evaluation_time_unknown_node_and_missing_formula_ref():
    logic_runtime = business_logic_runtime()
    assert_error(
        "NAIVE_EVALUATION_TIME",
        lambda: logic_runtime.materialize(
            contract(), "availability", inputs(), evaluated_at=NOW.replace(tzinfo=None)
        ),
    )
    assert_error(
        "NODE_NOT_FOUND",
        lambda: logic_runtime.materialize(contract(), "missing", inputs(), evaluated_at=NOW),
    )
    assert_error(
        "FORMULA_REF_REQUIRED",
        lambda: logic_runtime.materialize(
            contract(formula_ref=None), "availability", inputs(), evaluated_at=NOW
        ),
    )


def test_materialization_rejects_missing_formula_scope_unit_and_untrusted_function():
    empty_registry_runtime = PerformanceBusinessLogicRuntime(runtime_with_function(), BusinessLogicRegistry())
    assert_error(
        "FORMULA_NOT_FOUND",
        lambda: empty_registry_runtime.materialize(
            contract(), "availability", inputs(), evaluated_at=NOW
        ),
    )

    assert_error(
        "ORGANIZATION_SCOPE_MISMATCH",
        lambda: business_logic_runtime(
            logic=definition(organization_id="another-refinery")
        ).materialize(contract(), "availability", inputs(), evaluated_at=NOW),
    )
    assert_error(
        "OUTPUT_UNIT_MISMATCH",
        lambda: business_logic_runtime(logic=definition(output_unit="percent")).materialize(
            contract(), "availability", inputs(), evaluated_at=NOW
        ),
    )
    assert_error(
        "TRUSTED_FUNCTION_NOT_REGISTERED",
        lambda: business_logic_runtime(function_runtime=CEPIORuntime()).materialize(
            contract(), "availability", inputs(), evaluated_at=NOW
        ),
    )


def test_materialization_rejects_duplicate_missing_and_extra_inputs():
    logic_runtime = business_logic_runtime()
    duplicate = (
        inputs()[0],
        inputs()[0].model_copy(update={"value": 95.0}),
    )
    assert_error(
        "DUPLICATE_INPUT",
        lambda: logic_runtime.materialize(contract(), "availability", duplicate, evaluated_at=NOW),
    )
    assert_error(
        "INPUT_CONTRACT_MISMATCH",
        lambda: logic_runtime.materialize(
            contract(), "availability", (inputs()[0],), evaluated_at=NOW
        ),
    )
    extra = inputs() + (
        BusinessLogicInput(
            name="unplanned_input",
            value=1.0,
            observed_at=NOW,
            evidence_refs=("test:extra",),
        ),
    )
    assert_error(
        "INPUT_CONTRACT_MISMATCH",
        lambda: logic_runtime.materialize(contract(), "availability", extra, evaluated_at=NOW),
    )


def test_materialization_rejects_naive_future_and_stale_input_evidence():
    logic_runtime = business_logic_runtime()
    naive = list(inputs())
    naive[0] = naive[0].model_copy(update={"observed_at": NOW.replace(tzinfo=None)})
    assert_error(
        "NAIVE_INPUT_TIME",
        lambda: logic_runtime.materialize(contract(), "availability", naive, evaluated_at=NOW),
    )

    future = list(inputs())
    future[0] = future[0].model_copy(update={"observed_at": NOW + timedelta(seconds=1)})
    assert_error(
        "FUTURE_INPUT",
        lambda: logic_runtime.materialize(contract(), "availability", future, evaluated_at=NOW),
    )

    stale = list(inputs())
    stale[0] = stale[0].model_copy(update={"observed_at": NOW - timedelta(hours=2)})
    assert_error(
        "STALE_INPUT",
        lambda: logic_runtime.materialize(contract(), "availability", stale, evaluated_at=NOW),
    )


def test_materialization_wraps_function_failure_and_output_failures():
    assert_error(
        "FUNCTION_EXECUTION_FAILED",
        lambda: business_logic_runtime(
            function_runtime=runtime_with_function(
                handler=lambda runtime, uptime_hours, total_hours: (_ for _ in ()).throw(
                    RuntimeError("calculation failed")
                )
            )
        ).materialize(contract(), "availability", inputs(), evaluated_at=NOW),
    )

    missing_path_runtime = CEPIORuntime()
    missing_path_runtime.register_function(
        "calculateAvailability",
        lambda runtime, uptime_hours, total_hours: {"metrics": {"other": 1.0}},
        input_model=AvailabilityInputs,
    )
    assert_error(
        "OUTPUT_PATH_NOT_FOUND",
        lambda: business_logic_runtime(function_runtime=missing_path_runtime).materialize(
            contract(), "availability", inputs(), evaluated_at=NOW
        ),
    )

    non_numeric_runtime = CEPIORuntime()
    non_numeric_runtime.register_function(
        "calculateAvailability",
        lambda runtime, uptime_hours, total_hours: {"metrics": {"availability": "healthy"}},
        input_model=AvailabilityInputs,
    )
    assert_error(
        "NON_NUMERIC_OUTPUT",
        lambda: business_logic_runtime(function_runtime=non_numeric_runtime).materialize(
            contract(), "availability", inputs(), evaluated_at=NOW
        ),
    )

    boolean_runtime = CEPIORuntime()
    boolean_runtime.register_function(
        "calculateAvailability",
        lambda runtime, uptime_hours, total_hours: {"metrics": {"availability": True}},
        input_model=AvailabilityInputs,
    )
    assert_error(
        "NON_NUMERIC_OUTPUT",
        lambda: business_logic_runtime(function_runtime=boolean_runtime).materialize(
            contract(), "availability", inputs(), evaluated_at=NOW
        ),
    )

    non_finite_runtime = CEPIORuntime()
    non_finite_runtime.register_function(
        "calculateAvailability",
        lambda runtime, uptime_hours, total_hours: {"metrics": {"availability": float("nan")}},
        input_model=AvailabilityInputs,
    )
    assert_error(
        "NON_FINITE_OUTPUT",
        lambda: business_logic_runtime(function_runtime=non_finite_runtime).materialize(
            contract(), "availability", inputs(), evaluated_at=NOW
        ),
    )


def test_materialize_many_is_deterministic_and_rejects_duplicate_node_requests():
    logic_runtime = business_logic_runtime()
    request = BusinessLogicInvocation(node_id="availability", inputs=inputs())
    materialized = logic_runtime.materialize_many(contract(), [request], evaluated_at=NOW)
    assert len(materialized) == 1
    assert materialized[0].observation.value == 0.96
    assert_error(
        "DUPLICATE_NODE_INVOCATION",
        lambda: logic_runtime.materialize_many(contract(), [request, request], evaluated_at=NOW),
    )

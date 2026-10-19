from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from cepio.performance_contract import (
    PerformanceContract,
    PerformanceNode,
    PerformanceStatus,
    PerformanceSubject,
    PerformanceTarget,
)
from cepio.performance_runtime import PerformanceObservation, PerformanceRuntime


@pytest.mark.parametrize(
    ("target_kwargs", "message"),
    (
        ({"operator": "between", "upper_bound": 2}, "requires lower_bound and upper_bound"),
        (
            {"operator": "between", "lower_bound": 2, "upper_bound": 1},
            "lower_bound must not exceed upper_bound",
        ),
        (
            {"operator": "between", "value": 1, "lower_bound": 0, "upper_bound": 2},
            "must not set value",
        ),
        ({"operator": "gte"}, "requires value"),
        ({"operator": "gte", "value": 1, "lower_bound": 0}, "must not set bounds"),
    ),
)
def test_performance_target_rejects_invalid_shapes(target_kwargs, message):
    with pytest.raises(ValidationError, match=message):
        PerformanceTarget(**target_kwargs)


def test_performance_contract_and_node_reject_invalid_validity_windows():
    now = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)
    subject = PerformanceSubject(id="org", kind="enterprise", name="Org")

    with pytest.raises(ValidationError, match="valid_from must be before valid_to"):
        PerformanceNode(
            id="invalid-window",
            kind="kpi",
            name="Invalid window",
            scope_subject_id="org",
            valid_from=now,
            valid_to=now,
        )

    with pytest.raises(ValidationError, match="effective_from must be before effective_to"):
        PerformanceContract(
            id="invalid-contract-window",
            version="0.1.0",
            name="Invalid contract window",
            layer="organization",
            effective_from=now,
            effective_to=now,
            subjects=(subject,),
            nodes=(
                PerformanceNode(
                    id="kpi",
                    kind="kpi",
                    name="KPI",
                    scope_subject_id="org",
                ),
            ),
        )


def test_runtime_covers_eq_between_unscored_and_missing_node_lookup():
    now = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)
    contract = PerformanceContract(
        id="operators",
        version="0.1.0",
        name="Operator coverage",
        layer="organization",
        subjects=(PerformanceSubject(id="org", kind="enterprise", name="Org"),),
        nodes=(
            PerformanceNode(
                id="eq",
                kind="kpi",
                name="Equality KPI",
                scope_subject_id="org",
                target=PerformanceTarget(operator="eq", value=7),
            ),
            PerformanceNode(
                id="between",
                kind="kpi",
                name="Range KPI",
                scope_subject_id="org",
                target=PerformanceTarget(operator="between", lower_bound=1, upper_bound=2),
            ),
            PerformanceNode(
                id="raw",
                kind="metric",
                name="Raw metric",
                scope_subject_id="org",
            ),
        ),
    )

    result = PerformanceRuntime().evaluate(
        contract,
        (
            PerformanceObservation(
                node_id="eq", value=7, observed_at=now, evidence_refs=("source://eq",)
            ),
            PerformanceObservation(
                node_id="between",
                value=1.5,
                observed_at=now,
                evidence_refs=("source://between",),
            ),
            PerformanceObservation(
                node_id="raw", value=42, observed_at=now, evidence_refs=("source://raw",)
            ),
        ),
        evaluated_at=now,
    )

    assert result.node("eq").status == PerformanceStatus.on_track
    assert result.node("between").status == PerformanceStatus.on_track
    assert result.node("raw").status == PerformanceStatus.not_evaluated
    with pytest.raises(KeyError, match="missing"):
        result.node("missing")


def test_runtime_rejects_unknown_nodes_and_honors_node_validity_windows():
    now = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)
    contract = PerformanceContract(
        id="validity",
        version="0.1.0",
        name="Validity",
        layer="organization",
        subjects=(PerformanceSubject(id="org", kind="enterprise", name="Org"),),
        nodes=(
            PerformanceNode(
                id="future-valid",
                kind="kpi",
                name="Future-valid KPI",
                scope_subject_id="org",
                target=PerformanceTarget(operator="gte", value=1),
                valid_from=now,
            ),
            PerformanceNode(
                id="expired",
                kind="kpi",
                name="Expired KPI",
                scope_subject_id="org",
                target=PerformanceTarget(operator="gte", value=1),
                valid_to=now,
            ),
        ),
    )

    result = PerformanceRuntime().evaluate(
        contract,
        (
            PerformanceObservation(
                node_id="future-valid",
                value=2,
                observed_at=now - timedelta(seconds=1),
                evidence_refs=("source://before-validity",),
            ),
            PerformanceObservation(
                node_id="expired",
                value=2,
                observed_at=now,
                evidence_refs=("source://after-validity",),
            ),
        ),
        evaluated_at=now,
    )

    assert result.node("future-valid").status == PerformanceStatus.unknown
    assert "predates" in result.node("future-valid").reasons[0]
    assert result.node("expired").status == PerformanceStatus.unknown
    assert "outside" in result.node("expired").reasons[0]

    with pytest.raises(ValueError, match="unknown node"):
        PerformanceRuntime().evaluate(
            contract,
            (
                PerformanceObservation(
                    node_id="missing",
                    value=1,
                    observed_at=now,
                    evidence_refs=("source://missing",),
                ),
            ),
            evaluated_at=now,
        )

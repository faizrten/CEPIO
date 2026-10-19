from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from cepio.performance_contract import (
    PerformanceAccountability,
    PerformanceContract,
    PerformanceContribution,
    PerformanceNode,
    PerformanceResponseBinding,
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


def test_contract_rejects_self_edge_duplicate_ids_and_invalid_subject_links():
    subject = PerformanceSubject(id="org", kind="enterprise", name="Org")
    node = PerformanceNode(id="kpi", kind="kpi", name="KPI", scope_subject_id="org")

    with pytest.raises(ValidationError, match="self-edge"):
        PerformanceContribution(
            source_node_id="kpi",
            target_node_id="kpi",
            relation="contributes_to",
        )

    with pytest.raises(ValidationError, match="subject ids must be unique"):
        PerformanceContract(
            id="duplicate-subjects",
            version="0.1.0",
            name="Duplicate subjects",
            layer="organization",
            subjects=(subject, subject.model_copy()),
            nodes=(node,),
        )

    with pytest.raises(ValidationError, match="node ids must be unique"):
        PerformanceContract(
            id="duplicate-nodes",
            version="0.1.0",
            name="Duplicate nodes",
            layer="organization",
            subjects=(subject,),
            nodes=(node, node.model_copy()),
        )

    binding = PerformanceResponseBinding(
        id="binding",
        node_id="kpi",
        statuses=frozenset({"off_track"}),
        workflow_definition_id="workflow",
    )
    with pytest.raises(ValidationError, match="response binding ids must be unique"):
        PerformanceContract(
            id="duplicate-bindings",
            version="0.1.0",
            name="Duplicate bindings",
            layer="organization",
            subjects=(subject,),
            nodes=(node,),
            response_bindings=(binding, binding.model_copy()),
        )

    with pytest.raises(ValidationError, match="unknown parent subject"):
        PerformanceContract(
            id="unknown-parent",
            version="0.1.0",
            name="Unknown parent",
            layer="organization",
            subjects=(
                PerformanceSubject(
                    id="child", kind="function", name="Child", parent_id="missing"
                ),
            ),
            nodes=(
                PerformanceNode(id="child-kpi", kind="kpi", name="KPI", scope_subject_id="child"),
            ),
        )

    with pytest.raises(ValidationError, match="cannot parent itself"):
        PerformanceContract(
            id="self-parent",
            version="0.1.0",
            name="Self parent",
            layer="organization",
            subjects=(
                PerformanceSubject(id="org", kind="enterprise", name="Org", parent_id="org"),
            ),
            nodes=(node,),
        )

    with pytest.raises(ValidationError, match="unknown node scope subject"):
        PerformanceContract(
            id="unknown-scope",
            version="0.1.0",
            name="Unknown scope",
            layer="organization",
            subjects=(subject,),
            nodes=(PerformanceNode(id="kpi", kind="kpi", name="KPI", scope_subject_id="missing"),),
        )


def test_contract_rejects_all_dangling_performance_graph_references():
    subject = PerformanceSubject(id="org", kind="enterprise", name="Org")
    node_a = PerformanceNode(id="a", kind="kpi", name="A", scope_subject_id="org")
    node_b = PerformanceNode(id="b", kind="kpi", name="B", scope_subject_id="org")

    with pytest.raises(ValidationError, match="unknown accountability subject"):
        PerformanceContract(
            id="bad-accountability-subject",
            version="0.1.0",
            name="Bad accountability subject",
            layer="organization",
            subjects=(subject,),
            nodes=(node_a,),
            accountabilities=(
                PerformanceAccountability(
                    subject_id="missing", node_id="a", relation="accountable_for"
                ),
            ),
        )

    with pytest.raises(ValidationError, match="unknown contribution source"):
        PerformanceContract(
            id="bad-contribution-source",
            version="0.1.0",
            name="Bad contribution source",
            layer="organization",
            subjects=(subject,),
            nodes=(node_a, node_b),
            contributions=(
                PerformanceContribution(
                    source_node_id="missing", target_node_id="b", relation="contributes_to"
                ),
            ),
        )

    with pytest.raises(ValidationError, match="unknown contribution target"):
        PerformanceContract(
            id="bad-contribution-target",
            version="0.1.0",
            name="Bad contribution target",
            layer="organization",
            subjects=(subject,),
            nodes=(node_a, node_b),
            contributions=(
                PerformanceContribution(
                    source_node_id="a", target_node_id="missing", relation="contributes_to"
                ),
            ),
        )

    with pytest.raises(ValidationError, match="unknown response binding node"):
        PerformanceContract(
            id="bad-response-binding",
            version="0.1.0",
            name="Bad response binding",
            layer="organization",
            subjects=(subject,),
            nodes=(node_a,),
            response_bindings=(
                PerformanceResponseBinding(
                    id="binding",
                    node_id="missing",
                    statuses=frozenset({"off_track"}),
                    workflow_definition_id="workflow",
                ),
            ),
        )


def test_contract_rejects_subject_hierarchy_cycle():
    with pytest.raises(ValidationError, match="subject hierarchy must be acyclic"):
        PerformanceContract(
            id="subject-cycle",
            version="0.1.0",
            name="Subject cycle",
            layer="organization",
            subjects=(
                PerformanceSubject(id="a", kind="function", name="A", parent_id="b"),
                PerformanceSubject(id="b", kind="function", name="B", parent_id="a"),
            ),
            nodes=(PerformanceNode(id="kpi", kind="kpi", name="KPI", scope_subject_id="a"),),
        )


def test_runtime_rejects_naive_evaluation_time_and_ignores_future_observation():
    now = datetime(2026, 10, 19, 10, 0, tzinfo=timezone.utc)
    contract = PerformanceContract(
        id="runtime-time-boundaries",
        version="0.1.0",
        name="Runtime time boundaries",
        layer="organization",
        subjects=(PerformanceSubject(id="org", kind="enterprise", name="Org"),),
        nodes=(
            PerformanceNode(
                id="kpi",
                kind="kpi",
                name="KPI",
                scope_subject_id="org",
                target=PerformanceTarget(operator="gte", value=1),
            ),
        ),
    )

    with pytest.raises(ValueError, match="evaluated_at must be timezone-aware"):
        PerformanceRuntime().evaluate(
            contract,
            (),
            evaluated_at=datetime(2026, 10, 19, 10, 0),
        )

    result = PerformanceRuntime().evaluate(
        contract,
        (
            PerformanceObservation(
                node_id="kpi",
                value=2,
                observed_at=now + timedelta(seconds=1),
                evidence_refs=("source://future",),
            ),
        ),
        evaluated_at=now,
    )

    assert result.node("kpi").status == PerformanceStatus.unknown

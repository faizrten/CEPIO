from __future__ import annotations

from datetime import datetime, timezone

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
    PerformanceThreshold,
)
from cepio.performance_resolution import (
    PerformanceContractOverlay,
    PerformanceContractOverlayV2,
    PerformanceContractResolutionError,
    PerformanceContractResolver,
    PerformanceElementPatch,
    PerformanceElementSuppression,
    PerformanceFieldSet,
)
from cepio.performance_runtime import PerformanceObservation, PerformanceRuntime


def _root() -> PerformanceContract:
    return PerformanceContract(
        id="process-industry-reference-v02",
        version="0.2.0",
        name="Process industry reference",
        layer="industry_reference",
        subjects=(
            PerformanceSubject(id="industry", kind="enterprise", name="Industry reference"),
        ),
        nodes=(
            PerformanceNode(
                id="availability",
                kind="kpi",
                name="Operational availability",
                scope_subject_id="industry",
                unit="ratio",
                definition="Reference availability definition",
                formula_ref="logic://industry/availability/v1",
                target=PerformanceTarget(operator="gte", value=0.95),
                thresholds=(
                    PerformanceThreshold(
                        status="critical",
                        condition=PerformanceTarget(operator="lte", value=0.85),
                    ),
                ),
            ),
        ),
        response_bindings=(
            PerformanceResponseBinding(
                id="generic-availability-response",
                node_id="availability",
                statuses=frozenset({"off_track", "critical"}),
                workflow_definition_id="generic-availability-investigation",
            ),
        ),
    )


def _organization() -> PerformanceContractOverlayV2:
    return PerformanceContractOverlayV2(
        id="refinery-co-performance-v02",
        version="2.0.0",
        name="Refinery Co performance specialization",
        layer="organization",
        organization_id="refinery-co",
        extends_contract_id=_root().id,
        subjects=(
            PerformanceSubject(id="refinery-co", kind="enterprise", name="Refinery Co"),
            PerformanceSubject(
                id="operations",
                kind="function",
                name="Operations",
                parent_id="refinery-co",
            ),
        ),
        patches=(
            PerformanceElementPatch(
                element_type="node",
                element_key="availability",
                set_fields=(
                    PerformanceFieldSet(field="scope_subject_id", value="operations"),
                    PerformanceFieldSet(
                        field="definition", value="Refinery Co operational availability"
                    ),
                    PerformanceFieldSet(
                        field="formula_ref", value="logic://refinery-co/availability/v7"
                    ),
                    PerformanceFieldSet(
                        field="target",
                        value={"operator": "gte", "value": 0.97},
                    ),
                ),
                reason="Specialize the reference KPI to the organization's operating policy",
            ),
        ),
        suppressions=(
            PerformanceElementSuppression(
                element_type="response_binding",
                element_key="generic-availability-response",
                reason="Organization uses its governed reliability investigation workflow",
            ),
        ),
        response_bindings=(
            PerformanceResponseBinding(
                id="refinery-availability-response",
                node_id="availability",
                statuses=frozenset({"off_track", "critical"}),
                workflow_definition_id="refinery-availability-investigation",
            ),
        ),
    )


def _role() -> PerformanceContractOverlayV2:
    return PerformanceContractOverlayV2(
        id="reliability-role-performance-v02",
        version="2.0.0",
        name="Reliability Engineer performance specialization",
        layer="role",
        extends_contract_id=_organization().id,
        subjects=(
            PerformanceSubject(
                id="reliability-engineer",
                kind="persona",
                name="Reliability Engineer",
                parent_id="operations",
            ),
        ),
        nodes=(
            PerformanceNode(
                id="repeat-failures",
                kind="key_result",
                name="Reduce repeat compressor failures",
                scope_subject_id="reliability-engineer",
                target=PerformanceTarget(operator="lte", value=5),
            ),
        ),
        accountabilities=(
            PerformanceAccountability(
                subject_id="reliability-engineer",
                node_id="repeat-failures",
                relation="owns",
            ),
        ),
        contributions=(
            PerformanceContribution(
                source_node_id="repeat-failures",
                target_node_id="availability",
                relation="contributes_to",
                rationale="Repeat failures erode availability",
            ),
        ),
    )


def _individual() -> PerformanceContractOverlayV2:
    return PerformanceContractOverlayV2(
        id="engineer-42-performance-v02",
        version="2026.10.0",
        name="Engineer 42 performance specialization",
        layer="individual",
        extends_contract_id=_role().id,
        subjects=(
            PerformanceSubject(
                id="engineer-42",
                kind="individual",
                name="Engineer 42",
                parent_id="reliability-engineer",
            ),
        ),
        accountabilities=(
            PerformanceAccountability(
                subject_id="engineer-42",
                node_id="repeat-failures",
                relation="contributes_to",
            ),
        ),
    )


def _resolver() -> PerformanceContractResolver:
    return PerformanceContractResolver((_root(), _organization(), _role(), _individual()))


def test_v01_overlay_payload_shape_is_unchanged():
    overlay = PerformanceContractOverlay(
        id="legacy-overlay",
        version="1.0.0",
        name="Legacy overlay",
        layer="role",
        extends_contract_id="parent",
    )

    payload = overlay.model_dump(mode="json")
    assert payload["schema_version"] == "0.1.0"
    assert "patches" not in payload
    assert "suppressions" not in payload


def test_field_patch_specializes_kpi_without_copying_whole_node():
    result = _resolver().resolve(_individual().id)
    nodes = {node.id: node for node in result.contract.nodes}
    availability = nodes["availability"]

    assert result.contract.organization_id == "refinery-co"
    assert availability.kind.value == "kpi"
    assert availability.name == "Operational availability"
    assert availability.unit == "ratio"
    assert availability.scope_subject_id == "operations"
    assert availability.definition == "Refinery Co operational availability"
    assert availability.formula_ref == "logic://refinery-co/availability/v7"
    assert availability.target is not None
    assert availability.target.value == 0.97
    assert result.source_for("node", "availability").source_contract_id == _organization().id

    patch = next(
        operation
        for operation in result.operations
        if operation.operation == "patch" and operation.element_key == "availability"
    )
    assert patch.changed_fields == (
        "definition",
        "formula_ref",
        "scope_subject_id",
        "target",
    )


def test_role_and_individual_add_only_their_local_accountability():
    result = _resolver().resolve(_individual().id)
    subjects = {subject.id: subject for subject in result.contract.subjects}
    nodes = {node.id: node for node in result.contract.nodes}

    assert subjects["reliability-engineer"].kind.value == "persona"
    assert subjects["engineer-42"].kind.value == "individual"
    assert nodes["repeat-failures"].kind.value == "key_result"

    assignments = {
        (item.subject_id, item.node_id, item.relation.value)
        for item in result.contract.accountabilities
    }
    assert ("reliability-engineer", "repeat-failures", "owns") in assignments
    assert ("engineer-42", "repeat-failures", "contributes_to") in assignments
    assert ("engineer-42", "availability", "owns") not in assignments


def test_runtime_uses_effective_patched_target_and_org_response_binding():
    contract = _resolver().resolve(_individual().id).contract
    now = datetime(2026, 10, 20, 6, 0, tzinfo=timezone.utc)

    evaluation = PerformanceRuntime().evaluate(
        contract,
        (
            PerformanceObservation(
                node_id="availability",
                value=0.96,
                observed_at=now,
                evidence_refs=("pi://refinery/availability",),
            ),
        ),
        evaluated_at=now,
    )

    assert evaluation.node("availability").status == PerformanceStatus.off_track
    assert [candidate.workflow_definition_id for candidate in evaluation.workflow_candidates] == [
        "refinery-availability-investigation"
    ]


def test_suppression_removes_inherited_response_binding_and_is_audited():
    result = _resolver().resolve(_individual().id)
    binding_ids = {binding.id for binding in result.contract.response_bindings}

    assert "generic-availability-response" not in binding_ids
    assert "refinery-availability-response" in binding_ids
    suppression = next(
        operation
        for operation in result.operations
        if operation.operation == "suppress"
        and operation.element_key == "generic-availability-response"
    )
    assert suppression.source_contract_id == _organization().id
    assert "governed reliability" in (suppression.reason or "")


def test_patch_can_clear_inherited_optional_kpi_semantics():
    root = _root()
    org = PerformanceContractOverlayV2(
        id="clear-org",
        version="2.0.0",
        name="Clear inherited KPI policy",
        layer="organization",
        organization_id="org-a",
        extends_contract_id=root.id,
        patches=(
            PerformanceElementPatch(
                element_type="node",
                element_key="availability",
                clear_fields=frozenset({"formula_ref", "target", "thresholds"}),
            ),
        ),
    )

    availability = next(
        node
        for node in PerformanceContractResolver((root, org)).resolve(org.id).contract.nodes
        if node.id == "availability"
    )
    assert availability.formula_ref is None
    assert availability.target is None
    assert availability.thresholds == ()


def test_contribution_metadata_can_be_refined_field_by_field():
    root = PerformanceContract(
        id="contribution-root",
        version="1.0.0",
        name="Contribution root",
        layer="organization",
        organization_id="org-a",
        subjects=(PerformanceSubject(id="org", kind="enterprise", name="Org"),),
        nodes=(
            PerformanceNode(id="a", kind="kpi", name="A", scope_subject_id="org"),
            PerformanceNode(id="b", kind="objective", name="B", scope_subject_id="org"),
        ),
        contributions=(
            PerformanceContribution(
                source_node_id="a",
                target_node_id="b",
                relation="contributes_to",
                confidence=0.5,
            ),
        ),
    )
    role = PerformanceContractOverlayV2(
        id="contribution-role",
        version="2.0.0",
        name="Contribution role",
        layer="role",
        extends_contract_id=root.id,
        patches=(
            PerformanceElementPatch(
                element_type="contribution",
                element_key="a|b|contributes_to",
                set_fields=(PerformanceFieldSet(field="confidence", value=0.85),),
            ),
        ),
    )

    resolved = PerformanceContractResolver((root, role)).resolve(role.id)
    assert resolved.contract.contributions[0].confidence == 0.85
    assert (
        resolved.source_for("contribution", "a|b|contributes_to").source_contract_id
        == role.id
    )


@pytest.mark.parametrize("operation", ["patch", "suppress"])
def test_unknown_operation_target_fails_closed(operation: str):
    root = _root()
    kwargs = (
        {
            "patches": (
                PerformanceElementPatch(
                    element_type="node",
                    element_key="missing",
                    set_fields=(PerformanceFieldSet(field="name", value="Missing"),),
                ),
            )
        }
        if operation == "patch"
        else {
            "suppressions": (
                PerformanceElementSuppression(
                    element_type="node",
                    element_key="missing",
                    reason="Explicit test",
                ),
            )
        }
    )
    overlay = PerformanceContractOverlayV2(
        id=f"unknown-{operation}",
        version="2.0.0",
        name="Unknown target",
        layer="organization",
        organization_id="org-a",
        extends_contract_id=root.id,
        **kwargs,
    )

    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        PerformanceContractResolver((root, overlay)).resolve(overlay.id)
    assert exc_info.value.code == (
        "PATCH_TARGET_NOT_FOUND" if operation == "patch" else "SUPPRESSION_TARGET_NOT_FOUND"
    )


def test_suppression_is_non_cascading_and_final_graph_validation_still_fails_closed():
    root = PerformanceContract(
        id="dependency-root",
        version="1.0.0",
        name="Dependency root",
        layer="organization",
        organization_id="org-a",
        subjects=(PerformanceSubject(id="org", kind="enterprise", name="Org"),),
        nodes=(
            PerformanceNode(id="a", kind="kpi", name="A", scope_subject_id="org"),
            PerformanceNode(id="b", kind="objective", name="B", scope_subject_id="org"),
        ),
        contributions=(
            PerformanceContribution(
                source_node_id="a",
                target_node_id="b",
                relation="contributes_to",
            ),
        ),
    )
    role = PerformanceContractOverlayV2(
        id="bad-suppression",
        version="2.0.0",
        name="Bad suppression",
        layer="role",
        extends_contract_id=root.id,
        suppressions=(
            PerformanceElementSuppression(
                element_type="node",
                element_key="a",
                reason="Demonstrate non-cascading semantics",
            ),
        ),
    )

    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        PerformanceContractResolver((root, role)).resolve(role.id)
    assert exc_info.value.code == "INVALID_RESOLVED_CONTRACT"


def test_patch_rejects_identity_mutation_and_same_overlay_conflicts():
    with pytest.raises(ValidationError, match="cannot modify fields"):
        PerformanceElementPatch(
            element_type="node",
            element_key="availability",
            set_fields=(PerformanceFieldSet(field="kind", value="objective"),),
        )

    patch = PerformanceElementPatch(
        element_type="node",
        element_key="availability",
        set_fields=(PerformanceFieldSet(field="name", value="Local availability"),),
    )
    suppression = PerformanceElementSuppression(
        element_type="node",
        element_key="availability",
        reason="Conflict",
    )
    with pytest.raises(ValidationError, match="patch and suppress"):
        PerformanceContractOverlayV2(
            id="conflicting-overlay",
            version="2.0.0",
            name="Conflicting overlay",
            layer="organization",
            organization_id="org-a",
            extends_contract_id=_root().id,
            patches=(patch,),
            suppressions=(suppression,),
        )

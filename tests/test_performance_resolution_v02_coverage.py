from __future__ import annotations

import pytest
from pydantic import ValidationError

from cepio.performance_contract import (
    PerformanceAccountability,
    PerformanceContract,
    PerformanceContribution,
    PerformanceNode,
    PerformanceResponseBinding,
    PerformanceSubject,
)
from cepio.performance_registry import PerformanceContractRegistry
from cepio.performance_registry_v02 import SQLitePerformanceContractStoreV2
from cepio.performance_resolution import (
    PerformanceContractOverlayV2,
    PerformanceContractResolutionError,
    PerformanceContractResolver,
    PerformanceElementPatch,
    PerformanceElementSuppression,
    PerformanceFieldSet,
)


def _governance_root() -> PerformanceContract:
    return PerformanceContract(
        id="governance-root-v02",
        version="1.0.0",
        name="Governance root",
        layer="organization",
        organization_id="org-a",
        subjects=(
            PerformanceSubject(id="org", kind="enterprise", name="Org"),
            PerformanceSubject(id="spare", kind="team", name="Spare", parent_id="org"),
        ),
        nodes=(
            PerformanceNode(id="a", kind="kpi", name="A", scope_subject_id="org"),
            PerformanceNode(id="b", kind="objective", name="B", scope_subject_id="org"),
            PerformanceNode(id="c", kind="metric", name="C", scope_subject_id="org"),
        ),
        accountabilities=(
            PerformanceAccountability(
                subject_id="org",
                node_id="a",
                relation="accountable_for",
            ),
        ),
        contributions=(
            PerformanceContribution(
                source_node_id="a",
                target_node_id="b",
                relation="contributes_to",
                confidence=0.5,
            ),
        ),
        response_bindings=(
            PerformanceResponseBinding(
                id="response-a",
                node_id="a",
                statuses=frozenset({"off_track"}),
                workflow_definition_id="workflow-a",
            ),
        ),
    )


def test_patch_validator_rejects_ambiguous_operations():
    duplicate = PerformanceFieldSet(field="name", value="A")
    with pytest.raises(ValidationError, match="set fields must be unique"):
        PerformanceElementPatch(
            element_type="node",
            element_key="a",
            set_fields=(duplicate, duplicate.model_copy()),
        )

    with pytest.raises(ValidationError, match="set or clear at least one field"):
        PerformanceElementPatch(element_type="node", element_key="a")

    with pytest.raises(ValidationError, match="set and clear the same field"):
        PerformanceElementPatch(
            element_type="node",
            element_key="a",
            set_fields=(PerformanceFieldSet(field="description", value="local"),),
            clear_fields=frozenset({"description"}),
        )

    with pytest.raises(ValidationError, match="cannot clear fields"):
        PerformanceElementPatch(
            element_type="node",
            element_key="a",
            clear_fields=frozenset({"name"}),
        )


def test_overlay_v02_rejects_duplicate_operations_and_whole_entry_conflict():
    patch = PerformanceElementPatch(
        element_type="node",
        element_key="a",
        set_fields=(PerformanceFieldSet(field="name", value="A2"),),
    )
    with pytest.raises(ValidationError, match="patches must target unique elements"):
        PerformanceContractOverlayV2(
            id="duplicate-patches",
            version="2.0.0",
            name="Duplicate patches",
            layer="role",
            extends_contract_id="parent",
            patches=(patch, patch.model_copy()),
        )

    suppression = PerformanceElementSuppression(
        element_type="node",
        element_key="a",
        reason="test",
    )
    with pytest.raises(ValidationError, match="suppressions must target unique elements"):
        PerformanceContractOverlayV2(
            id="duplicate-suppressions",
            version="2.0.0",
            name="Duplicate suppressions",
            layer="role",
            extends_contract_id="parent",
            suppressions=(suppression, suppression.model_copy()),
        )

    with pytest.raises(ValidationError, match="conflicts with a whole-entry definition"):
        PerformanceContractOverlayV2(
            id="whole-entry-conflict",
            version="2.0.0",
            name="Whole entry conflict",
            layer="role",
            extends_contract_id="parent",
            nodes=(
                PerformanceNode(id="a", kind="kpi", name="Local A", scope_subject_id="org"),
            ),
            patches=(patch,),
        )


@pytest.mark.parametrize(
    ("element_type", "element_key", "absent_check"),
    (
        ("subject", "spare", lambda result: all(s.id != "spare" for s in result.contract.subjects)),
        ("node", "c", lambda result: all(n.id != "c" for n in result.contract.nodes)),
        (
            "accountability",
            "org|a|accountable_for",
            lambda result: not result.contract.accountabilities,
        ),
        (
            "contribution",
            "a|b|contributes_to",
            lambda result: not result.contract.contributions,
        ),
    ),
)
def test_suppression_handles_each_inherited_element_type(
    element_type: str,
    element_key: str,
    absent_check,
):
    root = _governance_root()
    overlay = PerformanceContractOverlayV2(
        id=f"suppress-{element_type}",
        version="2.0.0",
        name=f"Suppress {element_type}",
        layer="role",
        extends_contract_id=root.id,
        suppressions=(
            PerformanceElementSuppression(
                element_type=element_type,
                element_key=element_key,
                reason="explicit applicability decision",
            ),
        ),
    )
    resolved = PerformanceContractResolver((root, overlay)).resolve(overlay.id)
    assert absent_check(resolved)
    assert resolved.operations[-1].operation == "suppress"


def test_patch_handles_subject_and_response_binding_fields():
    root = _governance_root()
    overlay = PerformanceContractOverlayV2(
        id="patch-subject-response",
        version="2.0.0",
        name="Patch subject and response",
        layer="role",
        extends_contract_id=root.id,
        patches=(
            PerformanceElementPatch(
                element_type="subject",
                element_key="org",
                set_fields=(PerformanceFieldSet(field="name", value="Org refined"),),
            ),
            PerformanceElementPatch(
                element_type="response_binding",
                element_key="response-a",
                set_fields=(
                    PerformanceFieldSet(
                        field="statuses",
                        value=frozenset({"watch", "off_track"}),
                    ),
                    PerformanceFieldSet(
                        field="workflow_definition_id",
                        value="workflow-a-refined",
                    ),
                ),
            ),
        ),
    )
    resolved = PerformanceContractResolver((root, overlay)).resolve(overlay.id)
    subjects = {subject.id: subject for subject in resolved.contract.subjects}
    bindings = {binding.id: binding for binding in resolved.contract.response_bindings}
    assert subjects["org"].name == "Org refined"
    assert bindings["response-a"].workflow_definition_id == "workflow-a-refined"
    assert bindings["response-a"].statuses == frozenset({"watch", "off_track"})


def test_invalid_patch_value_fails_closed_during_effective_model_validation():
    root = _governance_root()
    overlay = PerformanceContractOverlayV2(
        id="invalid-patch-value",
        version="2.0.0",
        name="Invalid patch value",
        layer="role",
        extends_contract_id=root.id,
        patches=(
            PerformanceElementPatch(
                element_type="node",
                element_key="a",
                set_fields=(
                    PerformanceFieldSet(field="max_observation_age_seconds", value=-1),
                ),
            ),
        ),
    )
    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        PerformanceContractResolver((root, overlay)).resolve(overlay.id)
    assert exc_info.value.code == "INVALID_PATCH"


def test_unknown_contribution_patch_covers_missing_relationship_lookup():
    root = _governance_root()
    overlay = PerformanceContractOverlayV2(
        id="missing-contribution-patch",
        version="2.0.0",
        name="Missing contribution patch",
        layer="role",
        extends_contract_id=root.id,
        patches=(
            PerformanceElementPatch(
                element_type="contribution",
                element_key="missing|b|contributes_to",
                set_fields=(PerformanceFieldSet(field="confidence", value=0.8),),
            ),
        ),
    )
    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        PerformanceContractResolver((root, overlay)).resolve(overlay.id)
    assert exc_info.value.code == "PATCH_TARGET_NOT_FOUND"


def test_v02_sqlite_store_rejects_duplicate_revision_write(tmp_path):
    root = _governance_root()
    overlay = PerformanceContractOverlayV2(
        id="durable-v02-overlay",
        version="2.0.0",
        name="Durable v0.2 overlay",
        layer="role",
        extends_contract_id=root.id,
        patches=(
            PerformanceElementPatch(
                element_type="node",
                element_key="a",
                set_fields=(PerformanceFieldSet(field="name", value="A durable"),),
            ),
        ),
    )
    store = SQLitePerformanceContractStoreV2(tmp_path / "performance-duplicate.db")
    registry = PerformanceContractRegistry(store)
    registry.register(root, activate=True)
    revision = registry.register(overlay)

    with pytest.raises(ValueError, match="already exists"):
        store.create(revision)
    store.close()

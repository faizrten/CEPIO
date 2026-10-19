from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cepio.performance_contract import (
    PerformanceAccountability,
    PerformanceContract,
    PerformanceContractLayer,
    PerformanceContribution,
    PerformanceNode,
    PerformanceResponseBinding,
    PerformanceSubject,
)
from cepio.performance_resolution import (
    PerformanceContractOverlay,
    PerformanceContractResolutionError,
    PerformanceContractResolver,
)


def _subject(subject_id: str = "org") -> PerformanceSubject:
    return PerformanceSubject(id=subject_id, kind="enterprise", name=subject_id)


def _node(node_id: str, scope: str = "org") -> PerformanceNode:
    return PerformanceNode(id=node_id, kind="kpi", name=node_id, scope_subject_id=scope)


def test_overlay_rejects_invalid_window_parent_and_self_extension():
    start = datetime(2026, 10, 19, tzinfo=timezone.utc)

    with pytest.raises(ValueError, match="effective_from must be before effective_to"):
        PerformanceContractOverlay(
            id="bad-window",
            version="1",
            name="Bad window",
            layer="role",
            extends_contract_id="parent",
            effective_from=start,
            effective_to=start,
        )

    with pytest.raises(ValueError, match="requires extends_contract_id"):
        PerformanceContractOverlay(
            id="empty-parent",
            version="1",
            name="Empty parent",
            layer="role",
            extends_contract_id="",
        )

    with pytest.raises(ValueError, match="cannot extend itself"):
        PerformanceContractOverlay(
            id="self-parent",
            version="1",
            name="Self parent",
            layer="role",
            extends_contract_id="self-parent",
        )


def test_overlay_rejects_duplicate_element_identities():
    duplicate_subject = _subject("same-subject")
    with pytest.raises(ValueError, match="subject ids must be unique"):
        PerformanceContractOverlay(
            id="dup-subject",
            version="1",
            name="Duplicate subject",
            layer="role",
            extends_contract_id="parent",
            subjects=(duplicate_subject, duplicate_subject),
        )

    duplicate_node = _node("same-node", scope="inherited-subject")
    with pytest.raises(ValueError, match="node ids must be unique"):
        PerformanceContractOverlay(
            id="dup-node",
            version="1",
            name="Duplicate node",
            layer="role",
            extends_contract_id="parent",
            nodes=(duplicate_node, duplicate_node),
        )

    duplicate_binding = PerformanceResponseBinding(
        id="same-binding",
        node_id="inherited-node",
        statuses=frozenset({"off_track"}),
        workflow_definition_id="workflow-a",
    )
    with pytest.raises(ValueError, match="response binding ids must be unique"):
        PerformanceContractOverlay(
            id="dup-binding",
            version="1",
            name="Duplicate binding",
            layer="role",
            extends_contract_id="parent",
            response_bindings=(duplicate_binding, duplicate_binding),
        )

    duplicate_accountability = PerformanceAccountability(
        subject_id="inherited-subject",
        node_id="inherited-node",
        relation="owns",
    )
    with pytest.raises(ValueError, match="accountabilities must be unique"):
        PerformanceContractOverlay(
            id="dup-accountability",
            version="1",
            name="Duplicate accountability",
            layer="role",
            extends_contract_id="parent",
            accountabilities=(duplicate_accountability, duplicate_accountability),
        )

    duplicate_contribution = PerformanceContribution(
        source_node_id="source",
        target_node_id="target",
        relation="contributes_to",
    )
    with pytest.raises(ValueError, match="contributions must be unique"):
        PerformanceContractOverlay(
            id="dup-contribution",
            version="1",
            name="Duplicate contribution",
            layer="role",
            extends_contract_id="parent",
            contributions=(duplicate_contribution, duplicate_contribution),
        )


def test_complete_root_records_all_lineage_types_and_missing_lookup_fails_closed():
    accountability = PerformanceAccountability(
        subject_id="org",
        node_id="availability",
        relation="owns",
    )
    contribution = PerformanceContribution(
        source_node_id="repeat-failures",
        target_node_id="availability",
        relation="contributes_to",
    )
    binding = PerformanceResponseBinding(
        id="availability-response",
        node_id="availability",
        statuses=frozenset({"off_track", "critical"}),
        workflow_definition_id="investigate-availability",
    )
    root = PerformanceContract(
        id="org-performance",
        version="1",
        name="Organization performance",
        layer="organization",
        organization_id="org",
        subjects=(_subject(),),
        nodes=(_node("availability"), _node("repeat-failures")),
        accountabilities=(accountability,),
        contributions=(contribution,),
        response_bindings=(binding,),
    )

    resolved = PerformanceContractResolver((root,)).resolve(root.id)

    assert resolved.source_for("accountability", "org|availability|owns").source_contract_id == root.id
    assert (
        resolved.source_for(
            "contribution", "repeat-failures|availability|contributes_to"
        ).source_contract_id
        == root.id
    )
    assert (
        resolved.source_for("response_binding", "availability-response").source_contract_id
        == root.id
    )
    with pytest.raises(KeyError):
        resolved.source_for("node", "does-not-exist")


def test_response_binding_override_is_deterministic_and_traced_to_child():
    base_binding = PerformanceResponseBinding(
        id="availability-response",
        node_id="availability",
        statuses=frozenset({"off_track"}),
        workflow_definition_id="workflow-base",
    )
    base = PerformanceContract(
        id="org-base",
        version="1",
        name="Organization base",
        layer="organization",
        organization_id="org",
        subjects=(_subject(),),
        nodes=(_node("availability"),),
        response_bindings=(base_binding,),
    )
    override = base_binding.model_copy(update={"workflow_definition_id": "workflow-role"})
    role = PerformanceContractOverlay(
        id="role-overlay",
        version="1",
        name="Role overlay",
        layer="role",
        extends_contract_id=base.id,
        response_bindings=(override,),
    )

    resolved = PerformanceContractResolver((base, role)).resolve(role.id)

    assert resolved.contract.response_bindings[0].workflow_definition_id == "workflow-role"
    assert (
        resolved.source_for("response_binding", "availability-response").source_contract_id
        == role.id
    )


def test_resolver_rejects_tenant_bound_industry_reference():
    industry = PerformanceContract(
        id="tenant-bound-reference",
        version="1",
        name="Invalid tenant-bound reference",
        layer="industry_reference",
        organization_id="org-a",
        subjects=(_subject("reference"),),
        nodes=(),
    )

    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        PerformanceContractResolver((industry,)).resolve(industry.id)
    assert exc_info.value.code == "INDUSTRY_REFERENCE_TENANT_BOUND"


def test_resolver_requires_organization_id_on_organization_layer():
    organization = PerformanceContract(
        id="missing-org-id",
        version="1",
        name="Missing organization id",
        layer="organization",
        subjects=(_subject(),),
        nodes=(),
    )

    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        PerformanceContractResolver((organization,)).resolve(organization.id)
    assert exc_info.value.code == "ORGANIZATION_ID_REQUIRED"


def test_resolver_rejects_sparse_overlay_as_complete_root():
    malformed_root = PerformanceContractOverlay.model_construct(
        id="malformed-root",
        version="1",
        name="Malformed root",
        layer=PerformanceContractLayer.role,
        extends_contract_id=None,
        organization_id=None,
        effective_from=None,
        effective_to=None,
        subjects=(),
        nodes=(),
        accountabilities=(),
        contributions=(),
        response_bindings=(),
    )

    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        PerformanceContractResolver((malformed_root,)).resolve(malformed_root.id)
    assert exc_info.value.code == "ROOT_MUST_BE_COMPLETE"


def test_industry_reference_can_resolve_standalone_without_tenant_or_dates():
    industry = PerformanceContract(
        id="clean-industry-reference",
        version="1",
        name="Clean industry reference",
        layer="industry_reference",
        subjects=(_subject("reference"),),
        nodes=(),
    )

    resolved = PerformanceContractResolver((industry,)).resolve(industry.id)

    assert resolved.contract.organization_id is None
    assert resolved.contract.effective_from is None
    assert resolved.contract.effective_to is None
    assert resolved.source_contract_ids == (industry.id,)

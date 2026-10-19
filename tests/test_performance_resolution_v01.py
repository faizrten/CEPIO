from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cepio.performance_contract import (
    PerformanceAccountability,
    PerformanceContract,
    PerformanceContribution,
    PerformanceNode,
    PerformanceSubject,
    PerformanceTarget,
)
from cepio.performance_resolution import (
    PerformanceContractOverlay,
    PerformanceContractResolutionError,
    PerformanceContractResolver,
)
from cepio.performance_runtime import PerformanceObservation, PerformanceRuntime


def specialization_chain():
    industry = PerformanceContract(
        id="process-industry-reference",
        version="0.1.0",
        name="Process industry reference performance contract",
        layer="industry_reference",
        subjects=(
            PerformanceSubject(
                id="industry-reference", kind="enterprise", name="Industry reference"
            ),
        ),
        nodes=(
            PerformanceNode(
                id="reference-availability",
                kind="kpi",
                name="Operational availability reference",
                scope_subject_id="industry-reference",
                unit="ratio",
            ),
        ),
    )
    organization = PerformanceContractOverlay(
        id="refinery-co-performance",
        version="1.0.0",
        name="Refinery Co performance contract",
        layer="organization",
        organization_id="refinery-co",
        extends_contract_id=industry.id,
        subjects=(
            PerformanceSubject(id="refinery-co", kind="enterprise", name="Refinery Co"),
            PerformanceSubject(
                id="operations",
                kind="function",
                name="Operations",
                parent_id="refinery-co",
            ),
        ),
        nodes=(
            PerformanceNode(
                id="availability",
                kind="kpi",
                name="Operational availability",
                scope_subject_id="operations",
                unit="ratio",
                definition="Refinery Co operating availability",
                formula_ref="logic://refinery-co/availability/v7",
                reference_node_id="reference-availability",
                target=PerformanceTarget(operator="gte", value=0.96),
            ),
        ),
    )
    role = PerformanceContractOverlay(
        id="reliability-role-performance",
        version="1.0.0",
        name="Reliability role performance contract",
        layer="role",
        extends_contract_id=organization.id,
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
                id="availability",
                kind="kpi",
                name="Operational availability",
                scope_subject_id="operations",
                unit="ratio",
                definition="Refinery Co operating availability",
                formula_ref="logic://refinery-co/availability/v7",
                reference_node_id="reference-availability",
                target=PerformanceTarget(operator="gte", value=0.97),
            ),
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
            ),
        ),
    )
    individual = PerformanceContractOverlay(
        id="engineer-42-performance",
        version="2026.10.0",
        name="Engineer 42 performance contract",
        layer="individual",
        extends_contract_id=role.id,
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
    return industry, organization, role, individual


def test_resolves_industry_organization_role_individual_with_provenance():
    industry, organization, role, individual = specialization_chain()
    resolver = PerformanceContractResolver((industry, organization, role, individual))

    result = resolver.resolve(individual.id)
    contract = result.contract

    assert result.source_contract_ids == (
        industry.id,
        organization.id,
        role.id,
        individual.id,
    )
    assert contract.extends_contract_id is None
    assert contract.organization_id == "refinery-co"
    assert contract.layer.value == "individual"

    nodes = {node.id: node for node in contract.nodes}
    assert nodes["availability"].target is not None
    assert nodes["availability"].target.value == 0.97
    assert nodes["repeat-failures"].scope_subject_id == "reliability-engineer"

    assert result.source_for("node", "availability").source_contract_id == role.id
    assert result.source_for("node", "reference-availability").source_contract_id == industry.id
    assert result.source_for("subject", "engineer-42").source_contract_id == individual.id
    assert (
        result.source_for(
            "accountability", "engineer-42|repeat-failures|contributes_to"
        ).source_contract_id
        == individual.id
    )


def test_sparse_overlay_can_reference_inherited_subjects_and_nodes():
    industry, organization, role, individual = specialization_chain()
    result = PerformanceContractResolver((industry, organization, role, individual)).resolve(
        individual.id
    )

    subjects = {subject.id: subject for subject in result.contract.subjects}
    assert subjects["reliability-engineer"].parent_id == "operations"
    assert subjects["engineer-42"].parent_id == "reliability-engineer"

    edges = {
        (edge.source_node_id, edge.target_node_id, edge.relation.value)
        for edge in result.contract.contributions
    }
    assert ("repeat-failures", "availability", "contributes_to") in edges


def test_resolved_contract_is_directly_evaluable_by_existing_runtime():
    industry, organization, role, individual = specialization_chain()
    contract = (
        PerformanceContractResolver((industry, organization, role, individual))
        .resolve(individual.id)
        .contract
    )
    now = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)

    result = PerformanceRuntime().evaluate(
        contract,
        (
            PerformanceObservation(
                node_id="availability",
                value=0.965,
                observed_at=now,
                evidence_refs=("pi://refinery/availability",),
            ),
            PerformanceObservation(
                node_id="repeat-failures",
                value=7,
                observed_at=now,
                evidence_refs=("sap://failures/repeat",),
            ),
        ),
        evaluated_at=now,
    )

    assert result.node("availability").status.value == "off_track"
    assert result.node("repeat-failures").status.value == "off_track"


def test_child_can_refine_contribution_metadata_without_duplicate_edge():
    industry, organization, role, individual = specialization_chain()
    individual = individual.model_copy(
        update={
            "contributions": (
                PerformanceContribution(
                    source_node_id="repeat-failures",
                    target_node_id="availability",
                    relation="contributes_to",
                    confidence=0.8,
                    rationale="Locally validated contribution relationship",
                ),
            )
        }
    )
    result = PerformanceContractResolver((industry, organization, role, individual)).resolve(
        individual.id
    )

    matching = [
        edge
        for edge in result.contract.contributions
        if edge.source_node_id == "repeat-failures" and edge.target_node_id == "availability"
    ]
    assert len(matching) == 1
    assert matching[0].confidence == 0.8
    assert (
        result.source_for(
            "contribution", "repeat-failures|availability|contributes_to"
        ).source_contract_id
        == individual.id
    )


def test_rejects_node_and_subject_kind_mutation():
    industry, organization, role, _ = specialization_chain()
    bad_node = PerformanceContractOverlay(
        id="bad-node",
        version="1.0.0",
        name="Bad node",
        layer="individual",
        extends_contract_id=role.id,
        nodes=(
            PerformanceNode(
                id="availability",
                kind="objective",
                name="Mutated availability",
                scope_subject_id="operations",
            ),
        ),
    )
    resolver = PerformanceContractResolver((industry, organization, role, bad_node))
    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        resolver.resolve(bad_node.id)
    assert exc_info.value.code == "NODE_KIND_MUTATION"

    bad_subject = PerformanceContractOverlay(
        id="bad-subject",
        version="1.0.0",
        name="Bad subject",
        layer="individual",
        extends_contract_id=role.id,
        subjects=(
            PerformanceSubject(
                id="operations",
                kind="individual",
                name="Mutated operations",
            ),
        ),
    )
    resolver = PerformanceContractResolver((industry, organization, role, bad_subject))
    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        resolver.resolve(bad_subject.id)
    assert exc_info.value.code == "SUBJECT_KIND_MUTATION"


def test_rejects_missing_parent_and_inheritance_cycle():
    orphan = PerformanceContractOverlay(
        id="orphan",
        version="1.0.0",
        name="Orphan",
        layer="role",
        extends_contract_id="missing",
    )
    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        PerformanceContractResolver((orphan,)).resolve(orphan.id)
    assert exc_info.value.code == "CONTRACT_NOT_FOUND"

    first = PerformanceContractOverlay(
        id="first",
        version="1.0.0",
        name="First",
        layer="role",
        extends_contract_id="second",
    )
    second = PerformanceContractOverlay(
        id="second",
        version="1.0.0",
        name="Second",
        layer="individual",
        extends_contract_id="first",
    )
    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        PerformanceContractResolver((first, second)).resolve(second.id)
    assert exc_info.value.code == "INHERITANCE_CYCLE"


def test_rejects_overlay_root_and_layer_regression():
    root_overlay = PerformanceContractOverlay(
        id="root-overlay",
        version="1.0.0",
        name="Root overlay",
        layer="role",
        extends_contract_id="missing",
    )
    with pytest.raises(PerformanceContractResolutionError):
        PerformanceContractResolver((root_overlay,)).resolve(root_overlay.id)

    base = PerformanceContract(
        id="org-base",
        version="1.0.0",
        name="Org base",
        layer="organization",
        organization_id="org-a",
        subjects=(PerformanceSubject(id="org-a", kind="enterprise", name="Org A"),),
        nodes=(),
    )
    child = PerformanceContractOverlay(
        id="org-child",
        version="1.0.0",
        name="Org child",
        layer="organization",
        organization_id="org-a",
        extends_contract_id=base.id,
    )
    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        PerformanceContractResolver((base, child)).resolve(child.id)
    assert exc_info.value.code == "INVALID_LAYER_ORDER"


def test_rejects_cross_organization_specialization():
    base = PerformanceContract(
        id="org-a-contract",
        version="1.0.0",
        name="Org A",
        layer="organization",
        organization_id="org-a",
        subjects=(PerformanceSubject(id="org-a", kind="enterprise", name="Org A"),),
        nodes=(),
    )
    role = PerformanceContractOverlay(
        id="org-b-role",
        version="1.0.0",
        name="Org B role",
        layer="role",
        organization_id="org-b",
        extends_contract_id=base.id,
    )
    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        PerformanceContractResolver((base, role)).resolve(role.id)
    assert exc_info.value.code == "ORGANIZATION_BOUNDARY_VIOLATION"


def test_effective_window_is_intersection_and_empty_intersection_fails_closed():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    middle = datetime(2026, 6, 1, tzinfo=timezone.utc)
    end = datetime(2027, 1, 1, tzinfo=timezone.utc)
    base = PerformanceContract(
        id="window-base",
        version="1.0.0",
        name="Window base",
        layer="organization",
        organization_id="org-a",
        effective_from=start,
        effective_to=end,
        subjects=(PerformanceSubject(id="org-a", kind="enterprise", name="Org A"),),
        nodes=(),
    )
    child = PerformanceContractOverlay(
        id="window-role",
        version="1.0.0",
        name="Window role",
        layer="role",
        extends_contract_id=base.id,
        effective_from=middle,
    )
    resolved = PerformanceContractResolver((base, child)).resolve(child.id).contract
    assert resolved.effective_from == middle
    assert resolved.effective_to == end

    invalid = child.model_copy(
        update={
            "id": "invalid-window-role",
            "effective_from": datetime(2027, 2, 1, tzinfo=timezone.utc),
        }
    )
    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        PerformanceContractResolver((base, invalid)).resolve(invalid.id)
    assert exc_info.value.code == "EMPTY_EFFECTIVE_WINDOW"


def test_final_graph_validation_catches_dangling_sparse_reference():
    base = PerformanceContract(
        id="valid-base",
        version="1.0.0",
        name="Valid base",
        layer="organization",
        organization_id="org-a",
        subjects=(PerformanceSubject(id="org-a", kind="enterprise", name="Org A"),),
        nodes=(),
    )
    child = PerformanceContractOverlay(
        id="dangling-role",
        version="1.0.0",
        name="Dangling role",
        layer="role",
        extends_contract_id=base.id,
        nodes=(
            PerformanceNode(
                id="dangling-kpi",
                kind="kpi",
                name="Dangling KPI",
                scope_subject_id="missing-subject",
            ),
        ),
    )
    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        PerformanceContractResolver((base, child)).resolve(child.id)
    assert exc_info.value.code == "INVALID_RESOLVED_CONTRACT"


def test_registry_rejects_duplicate_active_contract_id():
    industry, _, _, _ = specialization_chain()
    resolver = PerformanceContractResolver((industry,))
    with pytest.raises(PerformanceContractResolutionError) as exc_info:
        resolver.register(industry)
    assert exc_info.value.code == "CONTRACT_ALREADY_REGISTERED"

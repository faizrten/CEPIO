from __future__ import annotations

from cepio.industry_performance_packs import (
    DRILLING_CONTRACTOR_PERFORMANCE_PACK_ID,
    REFINERY_PERFORMANCE_PACK_ID,
    drilling_contractor_performance_pack,
    industry_performance_pack,
    industry_performance_packs,
    refinery_performance_pack,
)
from cepio.performance_contract import (
    PerformanceAccountability,
    PerformanceSubject,
    PerformanceTarget,
)
from cepio.performance_resolution import (
    PerformanceContractOverlayV2,
    PerformanceContractResolver,
    PerformanceElementPatch,
    PerformanceElementSuppression,
    PerformanceFieldSet,
)


def _node(contract, node_id: str):
    return next(node for node in contract.nodes if node.id == node_id)


def test_built_in_performance_packs_are_organization_neutral_reference_contracts():
    packs = industry_performance_packs()

    assert tuple(pack.id for pack in packs) == (
        REFINERY_PERFORMANCE_PACK_ID,
        DRILLING_CONTRACTOR_PERFORMANCE_PACK_ID,
    )
    assert all(pack.layer.value == "industry_reference" for pack in packs)
    assert all(pack.organization_id is None for pack in packs)
    assert all(pack.extends_contract_id is None for pack in packs)
    assert all(pack.response_bindings == () for pack in packs)


def test_reference_kpis_do_not_claim_universal_formulas_targets_or_thresholds():
    for pack in industry_performance_packs():
        for node in pack.nodes:
            assert node.formula_ref is None
            assert node.target is None
            assert node.thresholds == ()


def test_refinery_pack_covers_economic_operating_reliability_energy_quality_and_guardrails():
    pack = refinery_performance_pack()
    nodes = {node.id: node for node in pack.nodes}
    subjects = {subject.name for subject in pack.subjects}

    expected = {
        "cepio.reference.refinery.kpi.operating-margin",
        "cepio.reference.refinery.kpi.operational-availability",
        "cepio.reference.refinery.kpi.production-throughput",
        "cepio.reference.refinery.kpi.production-loss",
        "cepio.reference.refinery.kpi.energy-intensity",
        "cepio.reference.refinery.kpi.product-spec-conformance",
        "cepio.reference.refinery.metric.unplanned-downtime",
        "cepio.reference.refinery.metric.repeat-equipment-failures",
        "cepio.reference.refinery.guardrail.process-safety-events",
        "cepio.reference.refinery.guardrail.environmental-limit-exceedances",
    }
    assert expected <= set(nodes)
    assert {
        "Plant Manager",
        "Operations Manager",
        "Reliability Engineer",
        "Process Engineer",
        "Energy Manager",
        "Quality Manager",
        "Process Safety Manager",
        "Environmental Manager",
        "Finance Controller",
        "Production Assurance Engineer",
    } <= subjects

    edge = next(
        item
        for item in pack.contributions
        if item.source_node_id == "cepio.reference.refinery.metric.repeat-equipment-failures"
        and item.target_node_id == "cepio.reference.refinery.metric.unplanned-downtime"
    )
    assert edge.relation.value == "contributes_to"


def test_drilling_pack_covers_fleet_operations_performance_commercial_and_safety():
    pack = drilling_contractor_performance_pack()
    nodes = {node.id: node for node in pack.nodes}
    subjects = {subject.name for subject in pack.subjects}

    expected = {
        "cepio.reference.drilling-contractor.kpi.contract-margin",
        "cepio.reference.drilling-contractor.kpi.fleet-utilization",
        "cepio.reference.drilling-contractor.kpi.operational-uptime",
        "cepio.reference.drilling-contractor.kpi.npt-ratio",
        "cepio.reference.drilling-contractor.kpi.dayrate-realization",
        "cepio.reference.drilling-contractor.metric.backlog-coverage",
        "cepio.reference.drilling-contractor.metric.npt-duration",
        "cepio.reference.drilling-contractor.metric.maintenance-downtime",
        "cepio.reference.drilling-contractor.metric.invisible-lost-time",
        "cepio.reference.drilling-contractor.metric.revenue-leakage",
        "cepio.reference.drilling-contractor.guardrail.serious-safety-events",
        "cepio.reference.drilling-contractor.guardrail.well-control-barrier-failures",
    }
    assert expected <= set(nodes)
    assert {
        "Chief Executive Officer / President",
        "Chief Operating Officer",
        "Chief Financial Officer",
        "VP / Director Drilling Operations",
        "Rig Manager",
        "Drilling Superintendent",
        "Reliability Engineer",
        "Drilling Performance / Optimization Engineer",
        "Commercial Manager",
        "HSE Manager",
        "Subsea / Well Control Engineer",
    } <= subjects

    ilt_edge = next(
        item
        for item in pack.contributions
        if item.source_node_id
        == "cepio.reference.drilling-contractor.metric.invisible-lost-time"
    )
    assert ilt_edge.target_node_id == "cepio.reference.drilling-contractor.kpi.npt-ratio"
    assert ilt_edge.relation.value == "influences"


def test_refinery_organization_can_specialize_only_owned_kpi_fields_and_accountability():
    reference = refinery_performance_pack()
    availability = "cepio.reference.refinery.kpi.operational-availability"
    reference_accountability = (
        "refinery.reference.operations-manager|" f"{availability}|accountable_for"
    )

    organization = PerformanceContractOverlayV2(
        id="example-refinery.performance",
        version="1.0.0",
        name="Example Refinery performance contract",
        layer="organization",
        organization_id="example-refinery",
        extends_contract_id=reference.id,
        subjects=(
            PerformanceSubject(
                id="example-refinery", kind="enterprise", name="Example Refinery"
            ),
            PerformanceSubject(
                id="example-refinery.operations",
                kind="function",
                name="Operations",
                parent_id="example-refinery",
            ),
            PerformanceSubject(
                id="example-refinery.coo",
                kind="role",
                name="Chief Operating Officer",
                parent_id="example-refinery.operations",
            ),
        ),
        patches=(
            PerformanceElementPatch(
                element_type="node",
                element_key=availability,
                set_fields=(
                    PerformanceFieldSet(
                        field="scope_subject_id", value="example-refinery.coo"
                    ),
                    PerformanceFieldSet(
                        field="formula_ref",
                        value="logic://example-refinery/operational-availability/v1",
                    ),
                    PerformanceFieldSet(
                        field="target", value={"operator": "gte", "value": 0.96}
                    ),
                ),
                reason="Bind reference availability to the organization's governed definition",
            ),
        ),
        suppressions=(
            PerformanceElementSuppression(
                element_type="accountability",
                element_key=reference_accountability,
                reason="Replace reference persona accountability with the local operating model",
            ),
        ),
        accountabilities=(
            PerformanceAccountability(
                subject_id="example-refinery.coo",
                node_id=availability,
                relation="accountable_for",
            ),
        ),
    )

    resolved = PerformanceContractResolver((reference, organization)).resolve(organization.id)
    effective = _node(resolved.contract, availability)

    assert effective.scope_subject_id == "example-refinery.coo"
    assert effective.formula_ref == "logic://example-refinery/operational-availability/v1"
    assert effective.target == PerformanceTarget(operator="gte", value=0.96)
    assert effective.name == "Operational availability"
    assert effective.unit == "ratio"
    assert resolved.contract.organization_id == "example-refinery"

    assignments = {
        f"{item.subject_id}|{item.node_id}|{item.relation.value}"
        for item in resolved.contract.accountabilities
    }
    assert reference_accountability not in assignments
    assert f"example-refinery.coo|{availability}|accountable_for" in assignments


def test_drilling_organization_can_bind_npt_policy_without_copying_reference_graph():
    reference = drilling_contractor_performance_pack()
    npt_ratio = "cepio.reference.drilling-contractor.kpi.npt-ratio"
    organization = PerformanceContractOverlayV2(
        id="example-drilling.performance",
        version="1.0.0",
        name="Example Drilling performance contract",
        layer="organization",
        organization_id="example-drilling",
        extends_contract_id=reference.id,
        patches=(
            PerformanceElementPatch(
                element_type="node",
                element_key=npt_ratio,
                set_fields=(
                    PerformanceFieldSet(
                        field="formula_ref", value="logic://example-drilling/npt-ratio/v3"
                    ),
                    PerformanceFieldSet(
                        field="target", value={"operator": "lte", "value": 0.05}
                    ),
                ),
                reason="Bind NPT to the contractor's activity taxonomy and performance target",
            ),
        ),
    )

    resolved = PerformanceContractResolver((reference, organization)).resolve(organization.id)
    effective = _node(resolved.contract, npt_ratio)

    assert effective.formula_ref == "logic://example-drilling/npt-ratio/v3"
    assert effective.target == PerformanceTarget(operator="lte", value=0.05)
    assert effective.definition == _node(reference, npt_ratio).definition
    assert len(resolved.contract.nodes) == len(reference.nodes)


def test_pack_lookup_uses_stable_contract_identity():
    refinery = industry_performance_pack(REFINERY_PERFORMANCE_PACK_ID)
    drilling = industry_performance_pack(DRILLING_CONTRACTOR_PERFORMANCE_PACK_ID)

    assert refinery.id == REFINERY_PERFORMANCE_PACK_ID
    assert drilling.id == DRILLING_CONTRACTOR_PERFORMANCE_PACK_ID

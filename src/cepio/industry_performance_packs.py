"""Canonical industry-reference Performance Contract packs.

These packs are reusable reference semantics, not customer policy. They deliberately
avoid customer-specific formulas, targets, thresholds and response bindings. An
organization opts into a pack by extending it with a PerformanceContractOverlayV2 and
specializes only the fields it owns.
"""

from __future__ import annotations

from .performance_contract import (
    AccountabilityRelation,
    ContributionRelation,
    PerformanceAccountability,
    PerformanceContract,
    PerformanceContractLayer,
    PerformanceContribution,
    PerformanceNode,
    PerformanceNodeKind,
    PerformanceSubject,
    PerformanceSubjectKind,
)

REFINERY_PERFORMANCE_PACK_ID = "cepio.performance.refinery.reference"
DRILLING_CONTRACTOR_PERFORMANCE_PACK_ID = "cepio.performance.drilling-contractor.reference"
INDUSTRY_PERFORMANCE_PACK_VERSION = "0.1.0"


def _persona(subject_id: str, name: str, parent_id: str) -> PerformanceSubject:
    return PerformanceSubject(
        id=subject_id,
        kind=PerformanceSubjectKind.persona,
        name=name,
        parent_id=parent_id,
    )


def _node(
    node_id: str,
    kind: PerformanceNodeKind,
    name: str,
    scope_subject_id: str,
    definition: str,
    *,
    unit: str | None = None,
) -> PerformanceNode:
    return PerformanceNode(
        id=node_id,
        kind=kind,
        name=name,
        scope_subject_id=scope_subject_id,
        unit=unit,
        definition=definition,
    )


def _accountability(
    subject_id: str,
    node_id: str,
    relation: AccountabilityRelation,
) -> PerformanceAccountability:
    return PerformanceAccountability(
        subject_id=subject_id,
        node_id=node_id,
        relation=relation,
    )


def _contribution(
    source_node_id: str,
    target_node_id: str,
    relation: ContributionRelation,
    rationale: str,
) -> PerformanceContribution:
    return PerformanceContribution(
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relation=relation,
        rationale=rationale,
    )


def refinery_performance_pack() -> PerformanceContract:
    """Return the organization-neutral refinery/process performance reference pack."""

    enterprise = "refinery.reference.enterprise"
    plant_manager = "refinery.reference.plant-manager"
    operations_manager = "refinery.reference.operations-manager"
    reliability_engineer = "refinery.reference.reliability-engineer"
    process_engineer = "refinery.reference.process-engineer"
    energy_manager = "refinery.reference.energy-manager"
    quality_manager = "refinery.reference.quality-manager"
    process_safety_manager = "refinery.reference.process-safety-manager"
    environmental_manager = "refinery.reference.environmental-manager"
    finance_controller = "refinery.reference.finance-controller"
    production_assurance_engineer = "refinery.reference.production-assurance-engineer"

    objective = "cepio.reference.refinery.objective.safe-resilient-profitable-operations"
    margin = "cepio.reference.refinery.kpi.operating-margin"
    availability = "cepio.reference.refinery.kpi.operational-availability"
    throughput = "cepio.reference.refinery.kpi.production-throughput"
    production_loss = "cepio.reference.refinery.kpi.production-loss"
    energy_intensity = "cepio.reference.refinery.kpi.energy-intensity"
    quality_conformance = "cepio.reference.refinery.kpi.product-spec-conformance"
    unplanned_downtime = "cepio.reference.refinery.metric.unplanned-downtime"
    repeat_failures = "cepio.reference.refinery.metric.repeat-equipment-failures"
    process_safety_events = "cepio.reference.refinery.guardrail.process-safety-events"
    environmental_exceedances = "cepio.reference.refinery.guardrail.environmental-limit-exceedances"

    return PerformanceContract(
        id=REFINERY_PERFORMANCE_PACK_ID,
        version=INDUSTRY_PERFORMANCE_PACK_VERSION,
        name="Refinery / process manufacturing reference performance pack",
        layer=PerformanceContractLayer.industry_reference,
        subjects=(
            PerformanceSubject(
                id=enterprise,
                kind=PerformanceSubjectKind.enterprise,
                name="Refinery reference",
            ),
            _persona(plant_manager, "Plant Manager", enterprise),
            _persona(operations_manager, "Operations Manager", plant_manager),
            _persona(reliability_engineer, "Reliability Engineer", operations_manager),
            _persona(process_engineer, "Process Engineer", operations_manager),
            _persona(energy_manager, "Energy Manager", plant_manager),
            _persona(quality_manager, "Quality Manager", plant_manager),
            _persona(process_safety_manager, "Process Safety Manager", plant_manager),
            _persona(environmental_manager, "Environmental Manager", plant_manager),
            _persona(finance_controller, "Finance Controller", plant_manager),
            _persona(
                production_assurance_engineer,
                "Production Assurance Engineer",
                operations_manager,
            ),
        ),
        nodes=(
            _node(
                objective,
                PerformanceNodeKind.objective,
                "Deliver safe, resilient and profitable refinery operations",
                plant_manager,
                "Reference enterprise objective. Each organization owns its exact objective "
                "wording, weighting and evaluation period.",
            ),
            _node(
                margin,
                PerformanceNodeKind.kpi,
                "Operating margin",
                finance_controller,
                "Reference economic-performance identity. Margin convention, price basis, "
                "transfer pricing, normalization and target are organization-specific.",
                unit="currency_per_throughput",
            ),
            _node(
                availability,
                PerformanceNodeKind.kpi,
                "Operational availability",
                operations_manager,
                "Reference availability identity. Formula, exclusions, denominator, aggregation "
                "and target remain external organization policy.",
                unit="ratio",
            ),
            _node(
                throughput,
                PerformanceNodeKind.kpi,
                "Production throughput",
                operations_manager,
                "Reference delivered-throughput identity; material basis, normalization, scope "
                "and plan comparison are organization-specific.",
                unit="volume_per_time",
            ),
            _node(
                production_loss,
                PerformanceNodeKind.kpi,
                "Production loss",
                production_assurance_engineer,
                "Reference lost-production identity; counterfactual capacity, attribution rules "
                "and economic conversion are organization-specific.",
                unit="volume",
            ),
            _node(
                energy_intensity,
                PerformanceNodeKind.kpi,
                "Energy intensity",
                energy_manager,
                "Reference energy-intensity identity. Denominator, unit, baseline, normalization "
                "and target remain contextual.",
                unit="energy_per_throughput",
            ),
            _node(
                quality_conformance,
                PerformanceNodeKind.kpi,
                "Product specification conformance",
                quality_manager,
                "Reference product-conformance identity; product slate, specification basis, "
                "disposition rules and target remain organization-specific.",
                unit="ratio",
            ),
            _node(
                unplanned_downtime,
                PerformanceNodeKind.metric,
                "Unplanned downtime",
                operations_manager,
                "Reference unplanned-downtime measure; event classification, clock basis and "
                "exclusions remain organization-specific.",
                unit="duration",
            ),
            _node(
                repeat_failures,
                PerformanceNodeKind.metric,
                "Repeat equipment failures",
                reliability_engineer,
                "Reference repeat-failure measure; recurrence window, failure taxonomy and asset "
                "scope remain organization-specific.",
                unit="count",
            ),
            _node(
                process_safety_events,
                PerformanceNodeKind.guardrail,
                "Process safety events",
                process_safety_manager,
                "Reference process-safety guardrail identity; event taxonomy, severity and "
                "reporting basis remain organization policy.",
                unit="count",
            ),
            _node(
                environmental_exceedances,
                PerformanceNodeKind.guardrail,
                "Environmental limit exceedances",
                environmental_manager,
                "Reference environmental-compliance guardrail; legal limits, averaging periods "
                "and reportability remain jurisdiction and organization specific.",
                unit="count",
            ),
        ),
        accountabilities=(
            _accountability(
                plant_manager,
                objective,
                AccountabilityRelation.accountable_for,
            ),
            _accountability(
                operations_manager,
                availability,
                AccountabilityRelation.accountable_for,
            ),
            _accountability(
                operations_manager,
                throughput,
                AccountabilityRelation.accountable_for,
            ),
            _accountability(reliability_engineer, repeat_failures, AccountabilityRelation.owns),
            _accountability(
                reliability_engineer,
                availability,
                AccountabilityRelation.contributes_to,
            ),
            _accountability(
                process_engineer,
                throughput,
                AccountabilityRelation.contributes_to,
            ),
            _accountability(energy_manager, energy_intensity, AccountabilityRelation.owns),
            _accountability(quality_manager, quality_conformance, AccountabilityRelation.owns),
            _accountability(
                process_safety_manager,
                process_safety_events,
                AccountabilityRelation.owns,
            ),
            _accountability(
                environmental_manager,
                environmental_exceedances,
                AccountabilityRelation.owns,
            ),
            _accountability(
                finance_controller,
                margin,
                AccountabilityRelation.accountable_for,
            ),
            _accountability(
                production_assurance_engineer,
                production_loss,
                AccountabilityRelation.owns,
            ),
        ),
        contributions=(
            _contribution(
                repeat_failures,
                unplanned_downtime,
                ContributionRelation.contributes_to,
                "Repeat equipment failures can create unplanned downtime.",
            ),
            _contribution(
                unplanned_downtime,
                availability,
                ContributionRelation.contributes_to,
                "Unplanned downtime is a driver of operational availability loss.",
            ),
            _contribution(
                availability,
                production_loss,
                ContributionRelation.contributes_to,
                "Availability loss can contribute to production loss.",
            ),
            _contribution(
                production_loss,
                margin,
                ContributionRelation.contributes_to,
                "Lost production can create economic margin exposure.",
            ),
            _contribution(
                throughput,
                margin,
                ContributionRelation.contributes_to,
                "Delivered throughput is a driver of refinery economic performance.",
            ),
            _contribution(
                energy_intensity,
                margin,
                ContributionRelation.contributes_to,
                "Energy performance can affect operating cost and margin.",
            ),
            _contribution(
                quality_conformance,
                margin,
                ContributionRelation.contributes_to,
                "Off-spec production can reduce realized product value.",
            ),
            _contribution(
                margin,
                objective,
                ContributionRelation.contributes_to,
                "Economic performance contributes to the enterprise objective.",
            ),
            _contribution(
                process_safety_events,
                objective,
                ContributionRelation.constrains,
                "Process safety is a non-negotiable operating guardrail.",
            ),
            _contribution(
                environmental_exceedances,
                objective,
                ContributionRelation.constrains,
                "Environmental compliance constrains acceptable performance.",
            ),
        ),
    )


def drilling_contractor_performance_pack() -> PerformanceContract:
    """Return the organization-neutral drilling-contractor performance reference pack."""

    enterprise = "drilling.reference.enterprise"
    chief_executive = "drilling.reference.chief-executive"
    chief_operating_officer = "drilling.reference.chief-operating-officer"
    chief_financial_officer = "drilling.reference.chief-financial-officer"
    vp_operations = "drilling.reference.vp-drilling-operations"
    rig_manager = "drilling.reference.rig-manager"
    drilling_superintendent = "drilling.reference.drilling-superintendent"
    reliability_engineer = "drilling.reference.reliability-engineer"
    drilling_performance_engineer = "drilling.reference.drilling-performance-engineer"
    commercial_manager = "drilling.reference.commercial-manager"
    hse_manager = "drilling.reference.hse-manager"
    well_control_engineer = "drilling.reference.subsea-well-control-engineer"

    objective = "cepio.reference.drilling-contractor.objective.safe-resilient-value-delivery"
    contract_margin = "cepio.reference.drilling-contractor.kpi.contract-margin"
    fleet_utilization = "cepio.reference.drilling-contractor.kpi.fleet-utilization"
    operational_uptime = "cepio.reference.drilling-contractor.kpi.operational-uptime"
    npt_ratio = "cepio.reference.drilling-contractor.kpi.npt-ratio"
    dayrate_realization = "cepio.reference.drilling-contractor.kpi.dayrate-realization"
    backlog_coverage = "cepio.reference.drilling-contractor.metric.backlog-coverage"
    npt_duration = "cepio.reference.drilling-contractor.metric.npt-duration"
    maintenance_downtime = "cepio.reference.drilling-contractor.metric.maintenance-downtime"
    invisible_lost_time = "cepio.reference.drilling-contractor.metric.invisible-lost-time"
    revenue_leakage = "cepio.reference.drilling-contractor.metric.revenue-leakage"
    safety_events = "cepio.reference.drilling-contractor.guardrail.serious-safety-events"
    well_control_failures = (
        "cepio.reference.drilling-contractor.guardrail.well-control-barrier-failures"
    )

    return PerformanceContract(
        id=DRILLING_CONTRACTOR_PERFORMANCE_PACK_ID,
        version=INDUSTRY_PERFORMANCE_PACK_VERSION,
        name="Drilling contractor reference performance pack",
        layer=PerformanceContractLayer.industry_reference,
        subjects=(
            PerformanceSubject(
                id=enterprise,
                kind=PerformanceSubjectKind.enterprise,
                name="Drilling contractor reference",
            ),
            _persona(
                chief_executive,
                "Chief Executive Officer / President",
                enterprise,
            ),
            _persona(chief_operating_officer, "Chief Operating Officer", chief_executive),
            _persona(chief_financial_officer, "Chief Financial Officer", chief_executive),
            _persona(
                vp_operations,
                "VP / Director Drilling Operations",
                chief_operating_officer,
            ),
            _persona(rig_manager, "Rig Manager", vp_operations),
            _persona(drilling_superintendent, "Drilling Superintendent", vp_operations),
            _persona(reliability_engineer, "Reliability Engineer", vp_operations),
            _persona(
                drilling_performance_engineer,
                "Drilling Performance / Optimization Engineer",
                vp_operations,
            ),
            _persona(commercial_manager, "Commercial Manager", chief_financial_officer),
            _persona(hse_manager, "HSE Manager", chief_operating_officer),
            _persona(well_control_engineer, "Subsea / Well Control Engineer", vp_operations),
        ),
        nodes=(
            _node(
                objective,
                PerformanceNodeKind.objective,
                "Deliver safe, resilient and economically valuable drilling services",
                chief_executive,
                "Reference drilling-contractor enterprise objective; exact strategic objectives, "
                "weights and evaluation periods are organization-specific.",
            ),
            _node(
                contract_margin,
                PerformanceNodeKind.kpi,
                "Contract margin",
                chief_financial_officer,
                "Reference contract-margin identity; recognized revenue, cost basis, allocation, "
                "currency and target remain organization policy.",
                unit="currency_per_period",
            ),
            _node(
                fleet_utilization,
                PerformanceNodeKind.kpi,
                "Fleet utilization",
                chief_operating_officer,
                "Reference fleet-utilization identity; marketed-fleet denominator, contract state, "
                "stacked-rig treatment and target remain contextual.",
                unit="ratio",
            ),
            _node(
                operational_uptime,
                PerformanceNodeKind.kpi,
                "Operational uptime",
                rig_manager,
                "Reference operational-uptime identity; planned exclusions, contractual clock, "
                "attributable downtime and target remain organization-specific.",
                unit="ratio",
            ),
            _node(
                npt_ratio,
                PerformanceNodeKind.kpi,
                "Non-productive-time ratio",
                drilling_superintendent,
                "Reference NPT-ratio identity; activity taxonomy, attribution, denominator and "
                "contractual treatment remain organization-specific.",
                unit="ratio",
            ),
            _node(
                dayrate_realization,
                PerformanceNodeKind.kpi,
                "Dayrate realization",
                commercial_manager,
                "Reference dayrate-realization identity; eligible time, rate basis, deductions, "
                "bonuses, penalties and target remain contract-specific.",
                unit="ratio",
            ),
            _node(
                backlog_coverage,
                PerformanceNodeKind.metric,
                "Contract backlog coverage",
                chief_executive,
                "Reference forward-coverage measure; backlog recognition, probability weighting "
                "and fleet denominator remain organization-specific.",
                unit="duration",
            ),
            _node(
                npt_duration,
                PerformanceNodeKind.metric,
                "Non-productive-time duration",
                drilling_superintendent,
                "Reference NPT duration; event classification, attribution and clock basis remain "
                "organization-specific.",
                unit="duration",
            ),
            _node(
                maintenance_downtime,
                PerformanceNodeKind.metric,
                "Maintenance downtime",
                reliability_engineer,
                "Reference maintenance-downtime measure; failure, planned-work and contractual "
                "classifications remain organization-specific.",
                unit="duration",
            ),
            _node(
                invisible_lost_time,
                PerformanceNodeKind.metric,
                "Invisible lost time",
                drilling_performance_engineer,
                "Reference drilling-efficiency loss measure; benchmark method, activity "
                "segmentation and comparison basis remain organization-specific.",
                unit="duration",
            ),
            _node(
                revenue_leakage,
                PerformanceNodeKind.metric,
                "Revenue leakage",
                commercial_manager,
                "Reference commercial leakage measure; contract entitlement, downtime attribution, "
                "deductions and claim status remain contract-specific.",
                unit="currency",
            ),
            _node(
                safety_events,
                PerformanceNodeKind.guardrail,
                "Serious safety events",
                hse_manager,
                "Reference safety guardrail identity; classification, severity, reporting basis and "
                "legal treatment remain organization/jurisdiction specific.",
                unit="count",
            ),
            _node(
                well_control_failures,
                PerformanceNodeKind.guardrail,
                "Well-control barrier failures",
                well_control_engineer,
                "Reference well-control barrier guardrail; barrier model, test validity, failure "
                "classification and reporting basis remain governed locally.",
                unit="count",
            ),
        ),
        accountabilities=(
            _accountability(
                chief_executive,
                objective,
                AccountabilityRelation.accountable_for,
            ),
            _accountability(
                chief_operating_officer,
                fleet_utilization,
                AccountabilityRelation.accountable_for,
            ),
            _accountability(
                chief_financial_officer,
                contract_margin,
                AccountabilityRelation.accountable_for,
            ),
            _accountability(
                vp_operations,
                npt_ratio,
                AccountabilityRelation.accountable_for,
            ),
            _accountability(
                rig_manager,
                operational_uptime,
                AccountabilityRelation.accountable_for,
            ),
            _accountability(drilling_superintendent, npt_duration, AccountabilityRelation.owns),
            _accountability(
                reliability_engineer, maintenance_downtime, AccountabilityRelation.owns
            ),
            _accountability(
                drilling_performance_engineer,
                invisible_lost_time,
                AccountabilityRelation.owns,
            ),
            _accountability(commercial_manager, dayrate_realization, AccountabilityRelation.owns),
            _accountability(commercial_manager, revenue_leakage, AccountabilityRelation.owns),
            _accountability(hse_manager, safety_events, AccountabilityRelation.owns),
            _accountability(
                well_control_engineer, well_control_failures, AccountabilityRelation.owns
            ),
        ),
        contributions=(
            _contribution(
                maintenance_downtime,
                operational_uptime,
                ContributionRelation.contributes_to,
                "Maintenance downtime is a driver of operational uptime loss.",
            ),
            _contribution(
                npt_duration,
                npt_ratio,
                ContributionRelation.contributes_to,
                "NPT duration is an input driver of the NPT ratio.",
            ),
            _contribution(
                npt_ratio,
                operational_uptime,
                ContributionRelation.contributes_to,
                "Material NPT can reduce productive operational uptime.",
            ),
            _contribution(
                operational_uptime,
                fleet_utilization,
                ContributionRelation.contributes_to,
                "Rig uptime supports delivered fleet utilization.",
            ),
            _contribution(
                invisible_lost_time,
                npt_ratio,
                ContributionRelation.influences,
                "Invisible lost time is relevant performance context but is not asserted as NPT "
                "without the organization's classification rules.",
            ),
            _contribution(
                fleet_utilization,
                contract_margin,
                ContributionRelation.contributes_to,
                "Fleet utilization is a driver of contractor economic performance.",
            ),
            _contribution(
                dayrate_realization,
                contract_margin,
                ContributionRelation.contributes_to,
                "Rate realization directly affects recognized contract economics.",
            ),
            _contribution(
                revenue_leakage,
                contract_margin,
                ContributionRelation.contributes_to,
                "Commercial leakage can reduce realized contract margin.",
            ),
            _contribution(
                backlog_coverage,
                objective,
                ContributionRelation.influences,
                "Backlog coverage informs resilience and capital allocation but is not treated as "
                "a deterministic causal driver in the reference graph.",
            ),
            _contribution(
                contract_margin,
                objective,
                ContributionRelation.contributes_to,
                "Economic performance contributes to enterprise value delivery.",
            ),
            _contribution(
                safety_events,
                objective,
                ContributionRelation.constrains,
                "Safety performance is a non-negotiable operating guardrail.",
            ),
            _contribution(
                well_control_failures,
                objective,
                ContributionRelation.constrains,
                "Well-control barrier integrity constrains acceptable performance.",
            ),
        ),
    )


def industry_performance_packs() -> tuple[PerformanceContract, ...]:
    """Return the currently qualified built-in industry performance reference packs."""

    return (refinery_performance_pack(), drilling_contractor_performance_pack())


def industry_performance_pack(pack_id: str) -> PerformanceContract:
    """Return one built-in reference pack by stable contract identity."""

    packs = {pack.id: pack for pack in industry_performance_packs()}
    try:
        return packs[pack_id]
    except KeyError as exc:
        raise KeyError(f"Unknown industry performance pack: {pack_id}") from exc


__all__ = [
    "DRILLING_CONTRACTOR_PERFORMANCE_PACK_ID",
    "INDUSTRY_PERFORMANCE_PACK_VERSION",
    "REFINERY_PERFORMANCE_PACK_ID",
    "drilling_contractor_performance_pack",
    "industry_performance_pack",
    "industry_performance_packs",
    "refinery_performance_pack",
]

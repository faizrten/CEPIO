"""Canonical industry-reference Performance Contract packs.

These packs are reusable reference semantics, not customer policy. They deliberately
avoid customer-specific formulas, targets, thresholds and response bindings. An
organization opts into a pack by extending it with a PerformanceContractOverlayV2 and
specializes only the fields it owns.
"""

from __future__ import annotations

from .performance_contract import (
    PerformanceAccountability,
    PerformanceContract,
    PerformanceContribution,
    PerformanceNode,
    PerformanceSubject,
)

REFINERY_PERFORMANCE_PACK_ID = "cepio.performance.refinery.reference"
DRILLING_CONTRACTOR_PERFORMANCE_PACK_ID = (
    "cepio.performance.drilling-contractor.reference"
)
INDUSTRY_PERFORMANCE_PACK_VERSION = "0.1.0"


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
    environmental_exceedances = (
        "cepio.reference.refinery.guardrail.environmental-limit-exceedances"
    )

    return PerformanceContract(
        id=REFINERY_PERFORMANCE_PACK_ID,
        version=INDUSTRY_PERFORMANCE_PACK_VERSION,
        name="Refinery / process manufacturing reference performance pack",
        layer="industry_reference",
        subjects=(
            PerformanceSubject(id=enterprise, kind="enterprise", name="Refinery reference"),
            PerformanceSubject(
                id=plant_manager,
                kind="persona",
                name="Plant Manager",
                parent_id=enterprise,
            ),
            PerformanceSubject(
                id=operations_manager,
                kind="persona",
                name="Operations Manager",
                parent_id=plant_manager,
            ),
            PerformanceSubject(
                id=reliability_engineer,
                kind="persona",
                name="Reliability Engineer",
                parent_id=operations_manager,
            ),
            PerformanceSubject(
                id=process_engineer,
                kind="persona",
                name="Process Engineer",
                parent_id=operations_manager,
            ),
            PerformanceSubject(
                id=energy_manager,
                kind="persona",
                name="Energy Manager",
                parent_id=plant_manager,
            ),
            PerformanceSubject(
                id=quality_manager,
                kind="persona",
                name="Quality Manager",
                parent_id=plant_manager,
            ),
            PerformanceSubject(
                id=process_safety_manager,
                kind="persona",
                name="Process Safety Manager",
                parent_id=plant_manager,
            ),
            PerformanceSubject(
                id=environmental_manager,
                kind="persona",
                name="Environmental Manager",
                parent_id=plant_manager,
            ),
            PerformanceSubject(
                id=finance_controller,
                kind="persona",
                name="Finance Controller",
                parent_id=plant_manager,
            ),
            PerformanceSubject(
                id=production_assurance_engineer,
                kind="persona",
                name="Production Assurance Engineer",
                parent_id=operations_manager,
            ),
        ),
        nodes=(
            PerformanceNode(
                id=objective,
                kind="objective",
                name="Deliver safe, resilient and profitable refinery operations",
                scope_subject_id=plant_manager,
                definition=(
                    "Reference enterprise objective. Each organization owns its exact "
                    "objective wording, weighting and evaluation period."
                ),
            ),
            PerformanceNode(
                id=margin,
                kind="kpi",
                name="Operating margin",
                scope_subject_id=finance_controller,
                unit="currency_per_throughput",
                definition=(
                    "Reference economic-performance identity. Margin convention, price "
                    "basis, transfer pricing, normalization and target are organization-specific."
                ),
            ),
            PerformanceNode(
                id=availability,
                kind="kpi",
                name="Operational availability",
                scope_subject_id=operations_manager,
                unit="ratio",
                definition=(
                    "Reference availability identity. Formula, exclusions, denominator, "
                    "aggregation and target remain external organization policy."
                ),
            ),
            PerformanceNode(
                id=throughput,
                kind="kpi",
                name="Production throughput",
                scope_subject_id=operations_manager,
                unit="volume_per_time",
                definition=(
                    "Reference delivered-throughput identity; material basis, normalization, "
                    "scope and plan comparison are organization-specific."
                ),
            ),
            PerformanceNode(
                id=production_loss,
                kind="kpi",
                name="Production loss",
                scope_subject_id=production_assurance_engineer,
                unit="volume",
                definition=(
                    "Reference lost-production identity; counterfactual capacity, attribution "
                    "rules and economic conversion are organization-specific."
                ),
            ),
            PerformanceNode(
                id=energy_intensity,
                kind="kpi",
                name="Energy intensity",
                scope_subject_id=energy_manager,
                unit="energy_per_throughput",
                definition=(
                    "Reference energy-intensity identity. Denominator, unit, baseline, "
                    "normalization and target remain contextual."
                ),
            ),
            PerformanceNode(
                id=quality_conformance,
                kind="kpi",
                name="Product specification conformance",
                scope_subject_id=quality_manager,
                unit="ratio",
                definition=(
                    "Reference product-conformance identity; product slate, specification "
                    "basis, disposition rules and target remain organization-specific."
                ),
            ),
            PerformanceNode(
                id=unplanned_downtime,
                kind="metric",
                name="Unplanned downtime",
                scope_subject_id=operations_manager,
                unit="duration",
                definition=(
                    "Reference unplanned-downtime measure; event classification, clock basis "
                    "and exclusions remain organization-specific."
                ),
            ),
            PerformanceNode(
                id=repeat_failures,
                kind="metric",
                name="Repeat equipment failures",
                scope_subject_id=reliability_engineer,
                unit="count",
                definition=(
                    "Reference repeat-failure measure; recurrence window, failure taxonomy "
                    "and asset scope remain organization-specific."
                ),
            ),
            PerformanceNode(
                id=process_safety_events,
                kind="guardrail",
                name="Process safety events",
                scope_subject_id=process_safety_manager,
                unit="count",
                definition=(
                    "Reference process-safety guardrail identity; event taxonomy, severity "
                    "and reporting basis remain organization policy."
                ),
            ),
            PerformanceNode(
                id=environmental_exceedances,
                kind="guardrail",
                name="Environmental limit exceedances",
                scope_subject_id=environmental_manager,
                unit="count",
                definition=(
                    "Reference environmental-compliance guardrail; legal limits, averaging "
                    "periods and reportability remain jurisdiction and organization specific."
                ),
            ),
        ),
        accountabilities=(
            PerformanceAccountability(
                subject_id=plant_manager,
                node_id=objective,
                relation="accountable_for",
            ),
            PerformanceAccountability(
                subject_id=operations_manager,
                node_id=availability,
                relation="accountable_for",
            ),
            PerformanceAccountability(
                subject_id=operations_manager,
                node_id=throughput,
                relation="accountable_for",
            ),
            PerformanceAccountability(
                subject_id=reliability_engineer,
                node_id=repeat_failures,
                relation="owns",
            ),
            PerformanceAccountability(
                subject_id=reliability_engineer,
                node_id=availability,
                relation="contributes_to",
            ),
            PerformanceAccountability(
                subject_id=process_engineer,
                node_id=throughput,
                relation="contributes_to",
            ),
            PerformanceAccountability(
                subject_id=energy_manager,
                node_id=energy_intensity,
                relation="owns",
            ),
            PerformanceAccountability(
                subject_id=quality_manager,
                node_id=quality_conformance,
                relation="owns",
            ),
            PerformanceAccountability(
                subject_id=process_safety_manager,
                node_id=process_safety_events,
                relation="owns",
            ),
            PerformanceAccountability(
                subject_id=environmental_manager,
                node_id=environmental_exceedances,
                relation="owns",
            ),
            PerformanceAccountability(
                subject_id=finance_controller,
                node_id=margin,
                relation="accountable_for",
            ),
            PerformanceAccountability(
                subject_id=production_assurance_engineer,
                node_id=production_loss,
                relation="owns",
            ),
        ),
        contributions=(
            PerformanceContribution(
                source_node_id=repeat_failures,
                target_node_id=unplanned_downtime,
                relation="contributes_to",
                rationale="Repeat equipment failures can create unplanned downtime.",
            ),
            PerformanceContribution(
                source_node_id=unplanned_downtime,
                target_node_id=availability,
                relation="contributes_to",
                rationale="Unplanned downtime is a driver of operational availability loss.",
            ),
            PerformanceContribution(
                source_node_id=availability,
                target_node_id=production_loss,
                relation="contributes_to",
                rationale="Availability loss can contribute to production loss.",
            ),
            PerformanceContribution(
                source_node_id=production_loss,
                target_node_id=margin,
                relation="contributes_to",
                rationale="Lost production can create economic margin exposure.",
            ),
            PerformanceContribution(
                source_node_id=throughput,
                target_node_id=margin,
                relation="contributes_to",
                rationale="Delivered throughput is a driver of refinery economic performance.",
            ),
            PerformanceContribution(
                source_node_id=energy_intensity,
                target_node_id=margin,
                relation="contributes_to",
                rationale="Energy performance can affect operating cost and margin.",
            ),
            PerformanceContribution(
                source_node_id=quality_conformance,
                target_node_id=margin,
                relation="contributes_to",
                rationale="Off-spec production can reduce realized product value.",
            ),
            PerformanceContribution(
                source_node_id=margin,
                target_node_id=objective,
                relation="contributes_to",
                rationale="Economic performance contributes to the enterprise objective.",
            ),
            PerformanceContribution(
                source_node_id=process_safety_events,
                target_node_id=objective,
                relation="constrains",
                rationale="Process safety is a non-negotiable operating guardrail.",
            ),
            PerformanceContribution(
                source_node_id=environmental_exceedances,
                target_node_id=objective,
                relation="constrains",
                rationale="Environmental compliance constrains acceptable performance.",
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
        layer="industry_reference",
        subjects=(
            PerformanceSubject(id=enterprise, kind="enterprise", name="Drilling contractor reference"),
            PerformanceSubject(
                id=chief_executive,
                kind="persona",
                name="Chief Executive Officer / President",
                parent_id=enterprise,
            ),
            PerformanceSubject(
                id=chief_operating_officer,
                kind="persona",
                name="Chief Operating Officer",
                parent_id=chief_executive,
            ),
            PerformanceSubject(
                id=chief_financial_officer,
                kind="persona",
                name="Chief Financial Officer",
                parent_id=chief_executive,
            ),
            PerformanceSubject(
                id=vp_operations,
                kind="persona",
                name="VP / Director Drilling Operations",
                parent_id=chief_operating_officer,
            ),
            PerformanceSubject(
                id=rig_manager,
                kind="persona",
                name="Rig Manager",
                parent_id=vp_operations,
            ),
            PerformanceSubject(
                id=drilling_superintendent,
                kind="persona",
                name="Drilling Superintendent",
                parent_id=vp_operations,
            ),
            PerformanceSubject(
                id=reliability_engineer,
                kind="persona",
                name="Reliability Engineer",
                parent_id=vp_operations,
            ),
            PerformanceSubject(
                id=drilling_performance_engineer,
                kind="persona",
                name="Drilling Performance / Optimization Engineer",
                parent_id=vp_operations,
            ),
            PerformanceSubject(
                id=commercial_manager,
                kind="persona",
                name="Commercial Manager",
                parent_id=chief_financial_officer,
            ),
            PerformanceSubject(
                id=hse_manager,
                kind="persona",
                name="HSE Manager",
                parent_id=chief_operating_officer,
            ),
            PerformanceSubject(
                id=well_control_engineer,
                kind="persona",
                name="Subsea / Well Control Engineer",
                parent_id=vp_operations,
            ),
        ),
        nodes=(
            PerformanceNode(
                id=objective,
                kind="objective",
                name="Deliver safe, resilient and economically valuable drilling services",
                scope_subject_id=chief_executive,
                definition=(
                    "Reference drilling-contractor enterprise objective; exact strategic "
                    "objectives, weights and evaluation periods are organization-specific."
                ),
            ),
            PerformanceNode(
                id=contract_margin,
                kind="kpi",
                name="Contract margin",
                scope_subject_id=chief_financial_officer,
                unit="currency_per_period",
                definition=(
                    "Reference contract-margin identity; recognized revenue, cost basis, "
                    "allocation, currency and target remain organization policy."
                ),
            ),
            PerformanceNode(
                id=fleet_utilization,
                kind="kpi",
                name="Fleet utilization",
                scope_subject_id=chief_operating_officer,
                unit="ratio",
                definition=(
                    "Reference fleet-utilization identity; marketed-fleet denominator, "
                    "contract state, stacked-rig treatment and target remain contextual."
                ),
            ),
            PerformanceNode(
                id=operational_uptime,
                kind="kpi",
                name="Operational uptime",
                scope_subject_id=rig_manager,
                unit="ratio",
                definition=(
                    "Reference operational-uptime identity; planned exclusions, contractual "
                    "clock, attributable downtime and target remain organization-specific."
                ),
            ),
            PerformanceNode(
                id=npt_ratio,
                kind="kpi",
                name="Non-productive-time ratio",
                scope_subject_id=drilling_superintendent,
                unit="ratio",
                definition=(
                    "Reference NPT-ratio identity; activity taxonomy, attribution, denominator "
                    "and contractual treatment remain organization-specific."
                ),
            ),
            PerformanceNode(
                id=dayrate_realization,
                kind="kpi",
                name="Dayrate realization",
                scope_subject_id=commercial_manager,
                unit="ratio",
                definition=(
                    "Reference dayrate-realization identity; eligible time, rate basis, "
                    "deductions, bonuses, penalties and target remain contract-specific."
                ),
            ),
            PerformanceNode(
                id=backlog_coverage,
                kind="metric",
                name="Contract backlog coverage",
                scope_subject_id=chief_executive,
                unit="duration",
                definition=(
                    "Reference forward-coverage measure; backlog recognition, probability "
                    "weighting and fleet denominator remain organization-specific."
                ),
            ),
            PerformanceNode(
                id=npt_duration,
                kind="metric",
                name="Non-productive-time duration",
                scope_subject_id=drilling_superintendent,
                unit="duration",
                definition=(
                    "Reference NPT duration; event classification, attribution and clock basis "
                    "remain organization-specific."
                ),
            ),
            PerformanceNode(
                id=maintenance_downtime,
                kind="metric",
                name="Maintenance downtime",
                scope_subject_id=reliability_engineer,
                unit="duration",
                definition=(
                    "Reference maintenance-downtime measure; failure, planned-work and "
                    "contractual classifications remain organization-specific."
                ),
            ),
            PerformanceNode(
                id=invisible_lost_time,
                kind="metric",
                name="Invisible lost time",
                scope_subject_id=drilling_performance_engineer,
                unit="duration",
                definition=(
                    "Reference drilling-efficiency loss measure; benchmark method, activity "
                    "segmentation and comparison basis remain organization-specific."
                ),
            ),
            PerformanceNode(
                id=revenue_leakage,
                kind="metric",
                name="Revenue leakage",
                scope_subject_id=commercial_manager,
                unit="currency",
                definition=(
                    "Reference commercial leakage measure; contract entitlement, downtime "
                    "attribution, deductions and claim status remain contract-specific."
                ),
            ),
            PerformanceNode(
                id=safety_events,
                kind="guardrail",
                name="Serious safety events",
                scope_subject_id=hse_manager,
                unit="count",
                definition=(
                    "Reference safety guardrail identity; classification, severity, reporting "
                    "basis and legal treatment remain organization/jurisdiction specific."
                ),
            ),
            PerformanceNode(
                id=well_control_failures,
                kind="guardrail",
                name="Well-control barrier failures",
                scope_subject_id=well_control_engineer,
                unit="count",
                definition=(
                    "Reference well-control barrier guardrail; barrier model, test validity, "
                    "failure classification and reporting basis remain governed locally."
                ),
            ),
        ),
        accountabilities=(
            PerformanceAccountability(
                subject_id=chief_executive,
                node_id=objective,
                relation="accountable_for",
            ),
            PerformanceAccountability(
                subject_id=chief_operating_officer,
                node_id=fleet_utilization,
                relation="accountable_for",
            ),
            PerformanceAccountability(
                subject_id=chief_financial_officer,
                node_id=contract_margin,
                relation="accountable_for",
            ),
            PerformanceAccountability(
                subject_id=vp_operations,
                node_id=npt_ratio,
                relation="accountable_for",
            ),
            PerformanceAccountability(
                subject_id=rig_manager,
                node_id=operational_uptime,
                relation="accountable_for",
            ),
            PerformanceAccountability(
                subject_id=drilling_superintendent,
                node_id=npt_duration,
                relation="owns",
            ),
            PerformanceAccountability(
                subject_id=reliability_engineer,
                node_id=maintenance_downtime,
                relation="owns",
            ),
            PerformanceAccountability(
                subject_id=drilling_performance_engineer,
                node_id=invisible_lost_time,
                relation="owns",
            ),
            PerformanceAccountability(
                subject_id=commercial_manager,
                node_id=dayrate_realization,
                relation="owns",
            ),
            PerformanceAccountability(
                subject_id=commercial_manager,
                node_id=revenue_leakage,
                relation="owns",
            ),
            PerformanceAccountability(
                subject_id=hse_manager,
                node_id=safety_events,
                relation="owns",
            ),
            PerformanceAccountability(
                subject_id=well_control_engineer,
                node_id=well_control_failures,
                relation="owns",
            ),
        ),
        contributions=(
            PerformanceContribution(
                source_node_id=maintenance_downtime,
                target_node_id=operational_uptime,
                relation="contributes_to",
                rationale="Maintenance downtime is a driver of operational uptime loss.",
            ),
            PerformanceContribution(
                source_node_id=npt_duration,
                target_node_id=npt_ratio,
                relation="contributes_to",
                rationale="NPT duration is an input driver of the NPT ratio.",
            ),
            PerformanceContribution(
                source_node_id=npt_ratio,
                target_node_id=operational_uptime,
                relation="contributes_to",
                rationale="Material NPT can reduce productive operational uptime.",
            ),
            PerformanceContribution(
                source_node_id=operational_uptime,
                target_node_id=fleet_utilization,
                relation="contributes_to",
                rationale="Rig uptime supports delivered fleet utilization.",
            ),
            PerformanceContribution(
                source_node_id=invisible_lost_time,
                target_node_id=npt_ratio,
                relation="influences",
                rationale=(
                    "Invisible lost time is relevant performance context but is not asserted "
                    "as NPT without the organization's classification rules."
                ),
            ),
            PerformanceContribution(
                source_node_id=fleet_utilization,
                target_node_id=contract_margin,
                relation="contributes_to",
                rationale="Fleet utilization is a driver of contractor economic performance.",
            ),
            PerformanceContribution(
                source_node_id=dayrate_realization,
                target_node_id=contract_margin,
                relation="contributes_to",
                rationale="Rate realization directly affects recognized contract economics.",
            ),
            PerformanceContribution(
                source_node_id=revenue_leakage,
                target_node_id=contract_margin,
                relation="contributes_to",
                rationale="Commercial leakage can reduce realized contract margin.",
            ),
            PerformanceContribution(
                source_node_id=backlog_coverage,
                target_node_id=objective,
                relation="influences",
                rationale=(
                    "Backlog coverage informs resilience and capital allocation but is not "
                    "treated as a deterministic causal driver in the reference graph."
                ),
            ),
            PerformanceContribution(
                source_node_id=contract_margin,
                target_node_id=objective,
                relation="contributes_to",
                rationale="Economic performance contributes to enterprise value delivery.",
            ),
            PerformanceContribution(
                source_node_id=safety_events,
                target_node_id=objective,
                relation="constrains",
                rationale="Safety performance is a non-negotiable operating guardrail.",
            ),
            PerformanceContribution(
                source_node_id=well_control_failures,
                target_node_id=objective,
                relation="constrains",
                rationale="Well-control barrier integrity constrains acceptable performance.",
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

"""Synthetic Rig 07 Performance Pack activation and deterministic acceptance example.

This example does not connect to customer systems, estimate EBITDA, initiate actions,
or assert a site-specific safety limit. Values and policy below are synthetic.
Run: PYTHONPATH=src python scripts/drilling_performance_activation_v01.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel, Field

from cepio.industry_performance_packs import drilling_contractor_performance_pack
from cepio.performance_business_logic import (
    BusinessLogicDefinition,
    BusinessLogicExecution,
    BusinessLogicInput,
    BusinessLogicInvocation,
    BusinessLogicRegistry,
    PerformanceBusinessLogicRuntime,
)
from cepio.performance_contract import (
    PerformanceAccountability,
    PerformanceContribution,
    PerformanceNode,
    PerformanceResponseBinding,
    PerformanceSubject,
)
from cepio.performance_registry import (
    InMemoryPerformanceContractStore,
    PerformanceContractRegistry,
    RegisteredPerformanceContractResolution,
)
from cepio.performance_resolution import (
    PerformanceContractOverlayV2,
    PerformanceElementPatch,
    PerformanceElementSuppression,
    PerformanceFieldSet,
)
from cepio.performance_runtime import PerformanceObservation as RuntimeObservation
from cepio.performance_service import PerformanceResponseAssessment, PerformanceService
from cepio.runtime import CEPIORuntime

ORG = "synthetic-rigco"
CONTRACT_ID = "synthetic-rigco.drilling-performance"
RIG_TEAM = "synthetic-rigco.rig-07-operations"
RIG_MANAGER = "synthetic-rigco.rig-07-manager"
NPT = "cepio.reference.drilling-contractor.kpi.npt-ratio"
UPTIME = "cepio.reference.drilling-contractor.kpi.operational-uptime"
LEAKAGE = "cepio.reference.drilling-contractor.metric.revenue-leakage"
SAFETY = "cepio.reference.drilling-contractor.guardrail.serious-safety-events"
WELL_CONTROL = "cepio.reference.drilling-contractor.guardrail.well-control-barrier-failures"
OBJECTIVE = "cepio.reference.drilling-contractor.objective.safe-resilient-value-delivery"
KR = "synthetic-rigco.rig-07.kr.reduce-equipment-npt"
NPT_FORMULA = "logic://synthetic-rigco/rig07/npt-ratio/v1"
UPTIME_FORMULA = "logic://synthetic-rigco/rig07/operational-uptime/v1"
LEAKAGE_FORMULA = "logic://synthetic-rigco/rig07/revenue-leakage/v1"
EVALUATED_AT = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)


class NptInputs(BaseModel):
    classified_npt_hours: float = Field(ge=0, allow_inf_nan=False)
    eligible_hours: float = Field(gt=0, allow_inf_nan=False)


class UptimeInputs(BaseModel):
    attributable_downtime_hours: float = Field(ge=0, allow_inf_nan=False)
    scheduled_hours: float = Field(gt=0, allow_inf_nan=False)


class LeakageInputs(BaseModel):
    confirmed_nonbillable_hours: float = Field(ge=0, allow_inf_nan=False)
    contractual_hourly_rate_usd: float = Field(ge=0, allow_inf_nan=False)


def _bounded_ratio(numerator: float, denominator: float) -> float:
    if numerator > denominator:
        raise ValueError("hours cannot exceed denominator")
    return numerator / denominator


def organization_overlay() -> PerformanceContractOverlayV2:
    """Explicit tenant-scoped policies; never mutate the industry reference pack."""
    reference = drilling_contractor_performance_pack()
    return PerformanceContractOverlayV2(
        id=CONTRACT_ID,
        version="0.1.0",
        name="SYNTHETIC RigCo Rig 07 performance activation",
        layer="organization",
        organization_id=ORG,
        extends_contract_id=reference.id,
        subjects=(
            PerformanceSubject(id=ORG, kind="enterprise", name="SYNTHETIC RigCo"),
            PerformanceSubject(
                id=RIG_TEAM, kind="team", name="Rig 07 operations", parent_id=ORG
            ),
            PerformanceSubject(
                id=RIG_MANAGER, kind="role", name="Rig 07 Manager", parent_id=RIG_TEAM
            ),
        ),
        nodes=(
            PerformanceNode(
                id=KR,
                kind="key_result",
                name="Reduce equipment-related Rig 07 NPT by 25% from 10% baseline",
                scope_subject_id=RIG_TEAM,
                unit="ratio",
                definition="Synthetic period KR: <= 7.5% by applying the approved NPT taxonomy.",
                formula_ref=NPT_FORMULA,
                target={"operator": "lte", "value": 0.075},
            ),
        ),
        patches=(
            PerformanceElementPatch(
                element_type="node",
                element_key=NPT,
                set_fields=(
                    PerformanceFieldSet(field="scope_subject_id", value=RIG_TEAM),
                    PerformanceFieldSet(field="formula_ref", value=NPT_FORMULA),
                    PerformanceFieldSet(
                        field="definition",
                        value="Classified equipment-related NPT hours / eligible rig hours.",
                    ),
                    PerformanceFieldSet(
                        field="target", value={"operator": "lte", "value": 0.08}
                    ),
                ),
                reason="Synthetic RigCo defines its own NPT clock, taxonomy and target.",
            ),
            PerformanceElementPatch(
                element_type="node",
                element_key=UPTIME,
                set_fields=(
                    PerformanceFieldSet(field="scope_subject_id", value=RIG_TEAM),
                    PerformanceFieldSet(field="formula_ref", value=UPTIME_FORMULA),
                    PerformanceFieldSet(
                        field="definition",
                        value="(Scheduled - attributable downtime) / scheduled hours.",
                    ),
                    PerformanceFieldSet(
                        field="target", value={"operator": "gte", "value": 0.95}
                    ),
                ),
                reason="Synthetic customer-specific operating uptime convention.",
            ),
            PerformanceElementPatch(
                element_type="node",
                element_key=LEAKAGE,
                set_fields=(
                    PerformanceFieldSet(field="formula_ref", value=LEAKAGE_FORMULA),
                    PerformanceFieldSet(
                        field="definition",
                        value="Confirmed nonbillable hours * approved contractual hourly rate; "
                        "synthetic gross revenue exposure, not EBITDA or cash loss.",
                    ),
                    PerformanceFieldSet(
                        field="target", value={"operator": "lte", "value": 0.0}
                    ),
                ),
                reason="Only contract-confirmed leakage may be quantified.",
            ),
            *(
                PerformanceElementPatch(
                    element_type="node",
                    element_key=node_id,
                    set_fields=(
                        PerformanceFieldSet(
                            field="target", value={"operator": "lte", "value": 0.0}
                        ),
                    ),
                    reason="Synthetic zero-incident guardrail, not a site safety limit.",
                )
                for node_id in (SAFETY, WELL_CONTROL)
            ),
        ),
        suppressions=(
            PerformanceElementSuppression(
                element_type="accountability",
                element_key=f"drilling.reference.rig-manager|{UPTIME}|accountable_for",
                reason="Replace archetypal rig manager with synthetic organization role.",
            ),
        ),
        accountabilities=(
            PerformanceAccountability(
                subject_id=RIG_MANAGER, node_id=UPTIME, relation="accountable_for"
            ),
            PerformanceAccountability(
                subject_id=RIG_MANAGER, node_id=KR, relation="contributes_to"
            ),
        ),
        contributions=(
            PerformanceContribution(
                source_node_id=NPT,
                target_node_id=KR,
                relation="depends_on",
                rationale="The KR evaluates the same locally defined NPT ratio.",
            ),
            PerformanceContribution(
                source_node_id=KR,
                target_node_id=OBJECTIVE,
                relation="contributes_to",
                rationale="Reduced equipment NPT supports resilient delivery.",
            ),
        ),
        response_bindings=(
            PerformanceResponseBinding(
                id="synthetic-rigco.rig07.npt-review",
                node_id=NPT,
                statuses=frozenset({"off_track", "critical"}),
                workflow_definition_id="drilling-rig07-reliability-investigation",
                rationale="Recommend a governed reliability investigation; no execution grant.",
            ),
        ),
    )


def _trusted_logic() -> PerformanceBusinessLogicRuntime:
    """Register only typed, reviewed functions, never user-authored expressions."""
    functions = CEPIORuntime()
    functions.register_function(
        "demo_rig07_npt_ratio",
        lambda runtime, classified_npt_hours, eligible_hours: _bounded_ratio(
            classified_npt_hours, eligible_hours
        ),
        input_model=NptInputs,
        output_type=float,
    )
    functions.register_function(
        "demo_rig07_uptime",
        lambda runtime, attributable_downtime_hours, scheduled_hours: 1.0
        - _bounded_ratio(attributable_downtime_hours, scheduled_hours),
        input_model=UptimeInputs,
        output_type=float,
    )
    functions.register_function(
        "demo_rig07_revenue_exposure",
        lambda runtime, confirmed_nonbillable_hours, contractual_hourly_rate_usd: (
            confirmed_nonbillable_hours * contractual_hourly_rate_usd
        ),
        input_model=LeakageInputs,
        output_type=float,
    )
    registry = BusinessLogicRegistry()
    for ref, function, names, unit in (
        (NPT_FORMULA, "demo_rig07_npt_ratio", ("classified_npt_hours", "eligible_hours"), "ratio"),
        (UPTIME_FORMULA, "demo_rig07_uptime", ("attributable_downtime_hours", "scheduled_hours"), "ratio"),
        (
            LEAKAGE_FORMULA,
            "demo_rig07_revenue_exposure",
            ("confirmed_nonbillable_hours", "contractual_hourly_rate_usd"),
            "currency",
        ),
    ):
        registry.register(
            BusinessLogicDefinition(
                formula_ref=ref,
                name=f"SYNTHETIC RigCo {function} v1",
                function_name=function,
                input_names=names,
                organization_id=ORG,
                output_unit=unit,
                max_input_age_seconds=86400,
            )
        )
    return PerformanceBusinessLogicRuntime(functions, registry)


def _input(name: str, value: float, evidence: str) -> BusinessLogicInput:
    return BusinessLogicInput(
        name=name,
        value=value,
        observed_at=EVALUATED_AT - timedelta(minutes=20),
        evidence_refs=(evidence,),
    )


@dataclass(frozen=True)
class ActivationResult:
    assessment: PerformanceResponseAssessment
    resolution: RegisteredPerformanceContractResolution
    business_logic_executions: tuple[BusinessLogicExecution, ...]


def run_activation(
    *,
    include_financial_evidence: bool = True,
    include_guardrail_evidence: bool = True,
) -> ActivationResult:
    """A complete, isolated synthetic scenario using qualified CEPIO runtimes."""
    registry = PerformanceContractRegistry(InMemoryPerformanceContractStore())
    reference = drilling_contractor_performance_pack()
    registry.register(reference, activate=True, created_at=EVALUATED_AT)
    registry.register(organization_overlay(), activate=True, created_at=EVALUATED_AT)
    resolution = registry.resolve(CONTRACT_ID, organization_id=ORG)
    contract = resolution.resolved.contract

    npt_inputs = (
        _input("classified_npt_hours", 12.0, "synthetic://rig07/npt-event-ledger"),
        _input("eligible_hours", 120.0, "synthetic://rig07/eligible-clock"),
    )
    invocations = [
        BusinessLogicInvocation(node_id=NPT, inputs=npt_inputs),
        BusinessLogicInvocation(node_id=KR, inputs=npt_inputs),
        BusinessLogicInvocation(
            node_id=UPTIME,
            inputs=(
                _input("attributable_downtime_hours", 12.0, "synthetic://rig07/downtime"),
                _input("scheduled_hours", 120.0, "synthetic://rig07/schedule"),
            ),
        ),
    ]
    if include_financial_evidence:
        invocations.append(
            BusinessLogicInvocation(
                node_id=LEAKAGE,
                inputs=(
                    _input(
                        "confirmed_nonbillable_hours",
                        8.0,
                        "synthetic://rig07/contract-confirmed-nonbillable-hours",
                    ),
                    _input(
                        "contractual_hourly_rate_usd",
                        4000.0,
                        "synthetic://rig07/approved-hourly-rate",
                    ),
                ),
            )
        )

    materialized = _trusted_logic().materialize_many(
        contract, invocations, evaluated_at=EVALUATED_AT
    )
    observations: list[RuntimeObservation] = [
        item.observation for item in materialized
    ]
    if include_guardrail_evidence:
        observations.extend(
            RuntimeObservation(
                node_id=node,
                value=0.0,
                observed_at=EVALUATED_AT - timedelta(minutes=10),
                evidence_refs=(f"synthetic://rig07/{name}-verified-register",),
            )
            for node, name in ( (SAFETY, "safety"), (WELL_CONTROL, "well-control") )
        )
    assessment = PerformanceService(registry).evaluate(
        CONTRACT_ID, observations, evaluated_at=EVALUATED_AT
    )
    return ActivationResult(
        assessment=assessment,
        resolution=resolution,
        business_logic_executions=tuple(item.execution for item in materialized),
    )


def main() -> None:
    result = run_activation()
    summary = {
        "synthetic": True,
        "organization": result.assessment.organization_id,
        "contract": result.assessment.contract_id,
        "source_revision_hashes": result.assessment.source_revision_hashes,
        "statuses": {
            node.node_id: {
                "status": node.status.value,
                "value": node.value,
                "evidence_refs": node.evidence_refs,
                "risk_sources": node.risk_sources,
            }
            for node in result.assessment.evaluation.nodes
        },
        "recommend_only_candidates": [
            candidate.model_dump(mode="json")
            for candidate in result.assessment.workflow_candidates
        ],
        "formula_provenance": [
            {"formula_ref": execution.formula_ref, "definition_hash": execution.definition_hash}
            for execution in result.business_logic_executions
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

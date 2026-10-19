from __future__ import annotations

from typing import Any

from .application_contract import (
    DecisionProposal,
    EvidenceReference,
    EvidenceRole,
    SkillExecutionHost,
    SkillExecutionOutput,
    SkillInvocation,
)
from .functions import MaintenanceDeferralRiskAssessment
from .model import ObjectRef
from .skill_preflight import (
    SkillAuthorityContract,
    SkillGraphPathRequirement,
    SkillGraphPathStep,
    SkillPreflightSpec,
)


MAINTENANCE_DEFERRAL_SKILL_ID = "cepio.skill.maintenance.assess-maintenance-deferral"

CORE = "https://cepio.org/ontology/core#"
IND = "https://cepio.org/ontology/industrial#"
REL = "https://cepio.org/ontology/reliability#"
PERF = "https://cepio.org/ontology/performance#"


def maintenance_deferral_skill_spec() -> SkillPreflightSpec:
    """Resolved runtime contract for the reference maintenance-deferral Skill."""

    return SkillPreflightSpec(
        skill_id=MAINTENANCE_DEFERRAL_SKILL_ID,
        binding_id="maintenance-deferral-v0.3",
        object_types={
            "Asset": CORE + "Asset",
            "Equipment": IND + "Equipment",
            "ConditionObservation": REL + "ConditionObservation",
            "WorkOrder": IND + "WorkOrder",
            "FailureEvent": REL + "FailureEvent",
            "FailureMode": REL + "FailureMode",
            "Risk": CORE + "Risk",
            "ProductionExposure": PERF + "ProductionExposure",
        },
        relationships={
            "hasConditionObservation": REL + "hasConditionObservation",
            "hasWorkOrder": IND + "hasWorkOrder",
            "failureOfEquipment": REL + "failureOfEquipment",
            "hasFailureMode": REL + "hasFailureMode",
            "hasRisk": CORE + "hasRisk",
        },
        functions={
            "calculate-production-exposure": "calculateProductionExposure",
            "evaluate-maintenance-risk": "evaluateMaintenanceDeferralRisk",
        },
        decisions={"maintenance-deferral-decision": "maintenance-deferral-decision"},
        actions={"defer-work-order": "DeferWorkOrder"},
        evidence_types={
            "Equipment",
            "ConditionObservation",
            "WorkOrder",
            "FailureEvent",
            "FailureMode",
            "Risk",
        },
        graph_paths=[
            SkillGraphPathRequirement(
                id="condition-evidence",
                start_type="Equipment",
                steps=[
                    SkillGraphPathStep(
                        relationship="hasConditionObservation",
                        target_type="ConditionObservation",
                    )
                ],
            ),
            SkillGraphPathRequirement(
                id="maintenance-item",
                start_type="Equipment",
                steps=[
                    SkillGraphPathStep(
                        relationship="hasWorkOrder",
                        target_type="WorkOrder",
                    )
                ],
            ),
            SkillGraphPathRequirement(
                id="risk-context",
                start_type="Equipment",
                steps=[
                    SkillGraphPathStep(
                        relationship="hasRisk",
                        target_type="Risk",
                    )
                ],
            ),
            SkillGraphPathRequirement(
                id="failure-history",
                start_type="Equipment",
                steps=[
                    SkillGraphPathStep(
                        relationship="failureOfEquipment",
                        direction="in",
                        target_type="FailureEvent",
                    ),
                    SkillGraphPathStep(
                        relationship="hasFailureMode",
                        target_type="FailureMode",
                    ),
                ],
            ),
        ],
        authority=SkillAuthorityContract(
            recommend=True,
            propose_decision=True,
            execute_actions=set(),
            approval_required_for={"defer-work-order"},
        ),
    )


def _required_string(parameters: dict[str, Any], name: str) -> str:
    value = parameters.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Maintenance deferral requires non-empty parameter {name}")
    return value


def _required_hours(parameters: dict[str, Any]) -> float:
    value = parameters.get("proposed_deferral_hours")
    try:
        hours = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "Maintenance deferral requires numeric parameter proposed_deferral_hours"
        ) from exc
    if hours < 0:
        raise ValueError("proposed_deferral_hours must be non-negative")
    return hours


def execute_maintenance_deferral(
    invocation: SkillInvocation,
    host: SkillExecutionHost,
) -> SkillExecutionOutput:
    """Evaluate one maintenance deferral without executing the work-order action.

    The procedure consumes governed Risk evidence through the existing deterministic
    runtime function. It may propose a CEPIO Decision, but direct ``DeferWorkOrder``
    execution remains outside the Skill and therefore inside the existing human/governed
    action boundary.
    """

    if invocation.skill_id != MAINTENANCE_DEFERRAL_SKILL_ID:
        raise ValueError(f"Unexpected Skill identity: {invocation.skill_id}")

    equipment = host.read_object(invocation.subject.id)
    work_order_id = _required_string(invocation.parameters, "work_order_id")
    risk_id = _required_string(invocation.parameters, "risk_id")
    proposed_hours = _required_hours(invocation.parameters)

    work_order = host.read_object(work_order_id)
    risk = host.read_object(risk_id)
    assessment = MaintenanceDeferralRiskAssessment.model_validate(
        host.call_function(
            "evaluateMaintenanceDeferralRisk",
            {
                "equipment_id": equipment.id,
                "work_order_id": work_order.id,
                "risk_id": risk.id,
                "proposed_deferral_hours": proposed_hours,
            },
        )
    )

    observations = [
        f"Current governed risk score: {assessment.current_risk_score:.3f}",
        f"Governed risk score under deferral: {assessment.deferral_risk_score:.3f}",
        f"Maximum supported deferral window: {assessment.max_supported_deferral_hours:g} hours",
        f"Requested deferral window: {assessment.proposed_deferral_hours:g} hours",
    ]

    if assessment.within_supported_window:
        recommendation = (
            "Deferral is supportable within the governed risk evidence; route the "
            "DeferWorkOrder action through its governed approval/execution path."
        )
        recommended_action = "DeferWorkOrder"
    else:
        recommendation = (
            "Do not defer the work order: the requested window is outside governed "
            "support or a hard constraint is present."
        )
        recommended_action = None

    decision = DecisionProposal(
        decision_type="maintenance-deferral-decision",
        subject=ObjectRef(id=work_order.id, type=work_order.type),
        problem=(
            f"Can work order {work_order.id} for equipment {equipment.id} be deferred "
            f"by {proposed_hours:g} hours?"
        ),
        observations=observations,
        recommendation=recommendation,
        recommended_action=recommended_action,
    )

    return SkillExecutionOutput(
        recommendation=recommendation,
        outputs={"risk_assessment": assessment.model_dump(mode="json")},
        evidence=[
            EvidenceReference(
                object_ref=ObjectRef(id=risk.id, type=risk.type),
                role=EvidenceRole.supporting,
            ),
            EvidenceReference(
                object_ref=ObjectRef(id=work_order.id, type=work_order.type),
                role=EvidenceRole.contextual,
            ),
        ],
        decision_proposal=decision,
        messages=[
            "DeferWorkOrder was not executed by the Skill; action authority remains governed separately."
        ],
    )

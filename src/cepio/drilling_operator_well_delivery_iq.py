from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from .model import ActionRequest, ObjectRef, OntologyObject, Relationship
from .runtime import CEPIORuntime


class WellDeliveryStatus(str, Enum):
    on_plan = "ON_PLAN"
    at_risk = "AT_RISK"
    intervention_required = "INTERVENTION_REQUIRED"


class WellDeliveryFinding(BaseModel):
    code: str
    severity: str
    message: str
    evidence_ids: list[str] = Field(default_factory=list)


class WellDeliveryInput(BaseModel):
    well_id: str
    approved_plan_id: str
    assessment_time: datetime
    activity_ids: list[str] = Field(min_length=1)
    plan_deviation_ids: list[str] = Field(default_factory=list)
    risk_ids: list[str] = Field(default_factory=list)


class WellDeliveryAssessment(BaseModel):
    well_id: str
    approved_plan_id: str
    assessment_time: datetime
    status: WellDeliveryStatus
    findings: list[WellDeliveryFinding]
    evidence_ids: list[str]
    recommendation: str


_NORMAL_ACTIVITY_STATUSES = {"PLANNED", "ACTIVE", "IN_PROGRESS", "COMPLETED", "COMPLETE"}
_BLOCKING_ACTIVITY_STATUSES = {"BLOCKED", "FAILED", "ABORTED"}
_CLOSED_STATUSES = {"CLOSED", "RESOLVED", "MITIGATED"}
_ACTIVE_STATUSES = {"OPEN", "ACTIVE"}
_ADVISORY_SEVERITIES = {"LOW", "MINOR", "ADVISORY", "MEDIUM"}
_BLOCKING_SEVERITIES = {"MATERIAL", "HIGH", "CRITICAL"}
_APPROVED_PLAN_STATUSES = {"APPROVED", "CURRENT", "ACTIVE"}


def _is_a(runtime: CEPIORuntime, actual_type: str, expected_type: str) -> bool:
    if runtime.type_registry is None:
        return actual_type == expected_type
    return runtime.type_registry.is_a(actual_type, expected_type)


def _require_type(runtime: CEPIORuntime, object_id: str, expected_type: str) -> OntologyObject:
    obj = runtime.get_object(object_id)
    if not _is_a(runtime, obj.type, expected_type):
        raise ValueError(f"{object_id} is not a {expected_type}")
    return obj


def _normalized_property(obj: OntologyObject, property_name: str) -> str:
    value = obj.properties.get(property_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{obj.id} is missing required normalized {property_name}")
    return value.strip().upper()


def _require_plan_scope(
    runtime: CEPIORuntime, approved_plan_id: str, well_id: str
) -> OntologyObject:
    plan = _require_type(runtime, approved_plan_id, "OperationalPlan")
    status = _normalized_property(plan, "status")
    if status not in _APPROVED_PLAN_STATUSES:
        raise ValueError(f"OperationalPlan {approved_plan_id} is not approved/current")
    scoped_well = plan.properties.get("wellId")
    if not isinstance(scoped_well, str) or not scoped_well.strip():
        raise ValueError(f"OperationalPlan {approved_plan_id} is missing governed wellId scope")
    if scoped_well != well_id:
        raise ValueError(
            f"OperationalPlan {approved_plan_id} is scoped to well {scoped_well}, not {well_id}"
        )
    return plan


def _activity_findings(
    runtime: CEPIORuntime, well_id: str, activity_ids: list[str]
) -> tuple[list[WellDeliveryFinding], list[str]]:
    findings: list[WellDeliveryFinding] = []
    evidence: list[str] = []
    for activity_id in activity_ids:
        activity = _require_type(runtime, activity_id, "ActivityInterval")
        evidence.append(activity_id)
        well_ids = {item.id for item in runtime.neighbors(activity_id, "activityForWell")}
        if well_id not in well_ids:
            raise ValueError(
                f"Activity {activity_id} is not linked to well {well_id} by activityForWell"
            )
        status = _normalized_property(activity, "status")
        if status in _BLOCKING_ACTIVITY_STATUSES:
            findings.append(
                WellDeliveryFinding(
                    code="execution.activity-blocked",
                    severity="blocking",
                    message=f"Activity {activity_id} has execution status {status}",
                    evidence_ids=[activity_id],
                )
            )
        elif status not in _NORMAL_ACTIVITY_STATUSES:
            raise ValueError(f"Activity {activity_id} has unsupported normalized status {status}")
    return findings, evidence


def _plan_deviation_findings(
    runtime: CEPIORuntime,
    well_id: str,
    approved_plan_id: str,
    activity_ids: list[str],
    deviation_ids: list[str],
) -> tuple[list[WellDeliveryFinding], list[str]]:
    findings: list[WellDeliveryFinding] = []
    evidence: list[str] = []
    allowed_scope = {well_id, *activity_ids}
    for deviation_id in deviation_ids:
        deviation = _require_type(runtime, deviation_id, "PlanDeviation")
        evidence.append(deviation_id)
        plan_ids = {item.id for item in runtime.neighbors(deviation_id, "deviationFromPlan")}
        if approved_plan_id not in plan_ids:
            raise ValueError(
                f"PlanDeviation {deviation_id} does not reference approved plan {approved_plan_id}"
            )
        impact_ids = {item.id for item in runtime.neighbors(deviation_id, "impacts")}
        if not impact_ids.intersection(allowed_scope):
            raise ValueError(
                f"PlanDeviation {deviation_id} is not scoped to well {well_id} or supplied activities"
            )
        status = _normalized_property(deviation, "status")
        if status in _CLOSED_STATUSES:
            continue
        if status not in _ACTIVE_STATUSES:
            raise ValueError(f"PlanDeviation {deviation_id} has unsupported status {status}")
        severity = _normalized_property(deviation, "severity")
        if severity in _BLOCKING_SEVERITIES:
            finding_severity = "blocking"
        elif severity in _ADVISORY_SEVERITIES:
            finding_severity = "advisory"
        else:
            raise ValueError(f"PlanDeviation {deviation_id} has unsupported severity {severity}")
        findings.append(
            WellDeliveryFinding(
                code="plan.active-deviation",
                severity=finding_severity,
                message=f"Active plan deviation {deviation_id} has severity {severity}",
                evidence_ids=[deviation_id],
            )
        )
    return findings, evidence


def _risk_findings(
    runtime: CEPIORuntime, well_id: str, activity_ids: list[str], risk_ids: list[str]
) -> tuple[list[WellDeliveryFinding], list[str]]:
    findings: list[WellDeliveryFinding] = []
    evidence: list[str] = []
    linked_risk_ids = {item.id for item in runtime.neighbors(well_id, "hasRisk")}
    for activity_id in activity_ids:
        linked_risk_ids.update(item.id for item in runtime.neighbors(activity_id, "hasRisk"))

    for risk_id in risk_ids:
        risk = _require_type(runtime, risk_id, "Risk")
        evidence.append(risk_id)
        if risk_id not in linked_risk_ids:
            raise ValueError(f"Risk {risk_id} is not governed by the assessed well/activity scope")
        status = _normalized_property(risk, "status")
        if status in _CLOSED_STATUSES:
            continue
        if status not in _ACTIVE_STATUSES:
            raise ValueError(f"Risk {risk_id} has unsupported status {status}")
        severity = _normalized_property(risk, "severity")
        if severity in _BLOCKING_SEVERITIES:
            finding_severity = "blocking"
        elif severity in _ADVISORY_SEVERITIES:
            finding_severity = "advisory"
        else:
            raise ValueError(f"Risk {risk_id} has unsupported severity {severity}")
        findings.append(
            WellDeliveryFinding(
                code="execution.active-risk",
                severity=finding_severity,
                message=f"Active execution risk {risk_id} has severity {severity}",
                evidence_ids=[risk_id],
            )
        )
    return findings, evidence


def assess_operator_well_delivery(
    *,
    runtime: CEPIORuntime,
    well_id: str,
    approved_plan_id: str,
    assessment_time: datetime,
    activity_ids: list[str],
    plan_deviation_ids: list[str] | None = None,
    risk_ids: list[str] | None = None,
) -> WellDeliveryAssessment:
    """Assess operator-owned well delivery from governed execution evidence.

    The result is an assessment, not a source-system fact. Contractor and service
    evidence may inform the result, but the approved plan and revision decision stay
    within the operator accountability boundary.
    """

    if assessment_time.tzinfo is None:
        raise ValueError("assessment_time must include timezone context")
    _require_type(runtime, well_id, "Well")
    _require_plan_scope(runtime, approved_plan_id, well_id)

    deviations = list(plan_deviation_ids or [])
    risks = list(risk_ids or [])
    activity_findings, activity_evidence = _activity_findings(runtime, well_id, activity_ids)
    deviation_findings, deviation_evidence = _plan_deviation_findings(
        runtime, well_id, approved_plan_id, activity_ids, deviations
    )
    risk_findings, risk_evidence = _risk_findings(runtime, well_id, activity_ids, risks)
    findings = [*activity_findings, *deviation_findings, *risk_findings]

    if any(item.severity == "blocking" for item in findings):
        status = WellDeliveryStatus.intervention_required
        recommendation = "Operator review and governed well-plan revision decision required."
    elif findings:
        status = WellDeliveryStatus.at_risk
        recommendation = "Continue with operator monitoring and resolve advisory deviations/risks."
    else:
        status = WellDeliveryStatus.on_plan
        recommendation = "Execution evidence remains aligned to the approved operator plan."

    evidence_ids = sorted(
        {
            well_id,
            approved_plan_id,
            *activity_evidence,
            *deviation_evidence,
            *risk_evidence,
        }
    )
    return WellDeliveryAssessment(
        well_id=well_id,
        approved_plan_id=approved_plan_id,
        assessment_time=assessment_time,
        status=status,
        findings=findings,
        evidence_ids=evidence_ids,
        recommendation=recommendation,
    )


def _require_well_target(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> tuple[bool, str]:
    return _is_a(runtime, target.type, "Well"), "Target must be a Well"


def _require_revision_rationale(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> tuple[bool, str]:
    return bool(request.parameters.get("rationale")), "Parameter rationale is required"


def _require_scoped_approved_plan(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> tuple[bool, str]:
    plan_id = request.parameters.get("plan_id")
    if not isinstance(plan_id, str) or not plan_id:
        return False, "Parameter plan_id is required"
    try:
        _require_plan_scope(runtime, plan_id, target.id)
    except (KeyError, ValueError) as exc:
        return False, str(exc)
    return True, "Approved plan scope is valid"


def initiate_well_plan_revision(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> dict[str, object]:
    plan_id = str(request.parameters["plan_id"])
    revision_id = str(request.parameters.get("revision_id", f"PLAN-REV-{uuid4().hex[:8].upper()}"))
    revision = OntologyObject(
        id=revision_id,
        type="PlanRevision",
        name=str(request.parameters.get("title", f"Plan revision review for {target.name}")),
        properties={
            "status": "DRAFT",
            "rationale": request.parameters["rationale"],
            "wellId": target.id,
            "assessmentStatus": request.parameters.get("assessment_status"),
            "evidenceIds": list(request.parameters.get("evidence_ids", [])),
            "createdBy": request.actor_id,
            "sourceAction": request.action_type,
        },
    )
    runtime.upsert_object(revision)
    runtime.add_relationship(
        Relationship(
            type="revisesPlan",
            source=ObjectRef(id=revision.id, type=revision.type),
            target=ObjectRef(id=plan_id, type="OperationalPlan"),
        )
    )
    runtime.add_relationship(
        Relationship(
            type="impacts",
            source=ObjectRef(id=revision.id, type=revision.type),
            target=ObjectRef(id=target.id, type=target.type),
        )
    )
    return {
        "plan_revision_id": revision.id,
        "plan_id": plan_id,
        "well_id": target.id,
        "external_side_effect": "not_configured",
    }


class DrillingOperatorWellDeliveryIndustryIQPack:
    pack_id = "cepio.iq.drilling.operator-well-delivery"
    version = "0.1.0"

    def install(self, runtime: CEPIORuntime) -> None:
        runtime.register_function(
            "assessOperatorWellDelivery",
            assess_operator_well_delivery,
            input_model=WellDeliveryInput,
            output_type=WellDeliveryAssessment,
        )
        runtime.register_action(
            "InitiateWellPlanRevision",
            initiate_well_plan_revision,
            {
                "operator_drilling_engineer",
                "operator_drilling_superintendent",
                "operator_wellsite_leader",
            },
            preconditions=[
                _require_well_target,
                _require_revision_rationale,
                _require_scoped_approved_plan,
            ],
            requires_human_approval=True,
        )
        runtime.register_decision(
            "operator-well-delivery-intervention-recommendation",
            allowed_subject_types={"Well"},
            allowed_actions={"InitiateWellPlanRevision"},
        )


DRILLING_OPERATOR_WELL_DELIVERY_IQ_PACK = DrillingOperatorWellDeliveryIndustryIQPack()

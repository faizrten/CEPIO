from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from .model import OntologyObject
from .runtime import CEPIORuntime


class AssetReliabilityStatus(str, Enum):
    reliable = "RELIABLE"
    degraded = "DEGRADED"
    intervention_required = "INTERVENTION_REQUIRED"


class ReliabilityFinding(BaseModel):
    code: str
    severity: str
    message: str
    evidence_ids: list[str] = Field(default_factory=list)


class AssetReliabilityInput(BaseModel):
    equipment_id: str
    assessment_time: datetime
    condition_observation_ids: list[str] = Field(min_length=1)
    failure_event_ids: list[str] = Field(default_factory=list)
    work_order_ids: list[str] = Field(default_factory=list)
    risk_ids: list[str] = Field(default_factory=list)


class AssetReliabilityAssessment(BaseModel):
    equipment_id: str
    assessed_at: datetime
    status: AssetReliabilityStatus
    findings: list[ReliabilityFinding]
    evidence_ids: list[str]
    recommended_action: str | None
    recommendation: str


_CURRENT_CONDITION = {"NORMAL", "HEALTHY", "ACCEPTABLE", "STABLE"}
_ADVISORY_CONDITION = {"DEGRADED", "WARNING", "ADVISORY"}
_BLOCKING_CONDITION = {"ABNORMAL", "ALARM", "CRITICAL", "FAILED"}
_CLOSED_STATUSES = {"CLOSED", "COMPLETE", "COMPLETED", "RESOLVED", "MITIGATED"}
_ACTIVE_FAILURE_STATUSES = {"OPEN", "ACTIVE", "IN_PROGRESS"}
_ACTIVE_RISK_STATUSES = {"OPEN", "ACTIVE"}
_ACTIVE_WORK_STATUSES = {"OPEN", "PLANNED", "CREATED", "IN_PROGRESS", "DEFERRED"}
_BLOCKING_WORK_STATUSES = {"BLOCKED", "OVERDUE"}
_ADVISORY_SEVERITIES = {"LOW", "MINOR", "MEDIUM", "ADVISORY"}
_BLOCKING_SEVERITIES = {"MATERIAL", "HIGH", "CRITICAL"}
_NORMAL_PRIORITIES = {"LOW", "MEDIUM", "NORMAL"}
_ADVISORY_PRIORITIES = {"HIGH"}
_BLOCKING_PRIORITIES = {"CRITICAL", "EMERGENCY"}
_REQUIRED_CORE_ACTIONS = {"CreateInspection", "CreateWorkOrder", "EscalateRisk"}
_REQUIRED_CORE_DECISION = "maintenance-intervention-recommendation"


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


def _aware_datetime(value: object, *, label: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{label} must be an ISO-8601 timestamp") from exc
    else:
        raise ValueError(f"{label} must be an ISO-8601 timestamp")
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must include timezone context")
    return parsed


def _require_current_evidence(obj: OntologyObject, assessment_time: datetime) -> None:
    valid_from = obj.properties.get("validFrom")
    if valid_from is not None:
        start = _aware_datetime(valid_from, label=f"{obj.id} validFrom")
        if start > assessment_time:
            raise ValueError(f"{obj.id} is not yet valid at assessment time")

    valid_to = obj.properties.get("validTo")
    if valid_to is None:
        raise ValueError(f"{obj.id} is missing required validity horizon validTo")
    end = _aware_datetime(valid_to, label=f"{obj.id} validTo")
    if end <= assessment_time:
        raise ValueError(f"{obj.id} is stale at assessment time")


def _condition_band(status: str) -> str:
    if status in _CURRENT_CONDITION:
        return "normal"
    if status in _ADVISORY_CONDITION:
        return "advisory"
    if status in _BLOCKING_CONDITION:
        return "blocking"
    raise ValueError(f"Unsupported normalized condition status {status}")


def _severity_band(severity: str) -> str:
    if severity in _ADVISORY_SEVERITIES:
        return "advisory"
    if severity in _BLOCKING_SEVERITIES:
        return "blocking"
    raise ValueError(f"Unsupported normalized severity {severity}")


def _assess_condition(
    runtime: CEPIORuntime,
    equipment_id: str,
    assessment_time: datetime,
    condition_ids: list[str],
) -> tuple[list[ReliabilityFinding], set[str]]:
    linked = {item.id for item in runtime.neighbors(equipment_id, "hasConditionObservation")}
    findings: list[ReliabilityFinding] = []
    evidence: set[str] = set()
    signal_bands: dict[str, set[str]] = {}

    for condition_id in condition_ids:
        observation = _require_type(runtime, condition_id, "ConditionObservation")
        if observation.id not in linked:
            raise ValueError(
                f"ConditionObservation {observation.id} is not linked to equipment {equipment_id}"
            )
        _require_current_evidence(observation, assessment_time)
        evidence.add(observation.id)
        status = _normalized_property(observation, "status")
        band = _condition_band(status)

        signal_key = observation.properties.get("signalKey")
        if isinstance(signal_key, str) and signal_key.strip():
            signal_bands.setdefault(signal_key.strip(), set()).add(band)

        if band == "advisory":
            findings.append(
                ReliabilityFinding(
                    code="condition.degraded",
                    severity="advisory",
                    message=f"Condition observation {observation.id} is {status}",
                    evidence_ids=[observation.id],
                )
            )
        elif band == "blocking":
            findings.append(
                ReliabilityFinding(
                    code="condition.material-degradation",
                    severity="blocking",
                    message=f"Condition observation {observation.id} is {status}",
                    evidence_ids=[observation.id],
                )
            )

    for signal_key, bands in signal_bands.items():
        if "normal" in bands and len(bands) > 1:
            raise ValueError(
                f"Conflicting current condition evidence for signalKey {signal_key}"
            )

    return findings, evidence


def _assess_failures(
    runtime: CEPIORuntime,
    equipment_id: str,
    failure_ids: list[str],
) -> tuple[list[ReliabilityFinding], set[str]]:
    findings: list[ReliabilityFinding] = []
    evidence: set[str] = set()

    for failure_id in failure_ids:
        failure = _require_type(runtime, failure_id, "FailureEvent")
        targets = {item.id for item in runtime.neighbors(failure.id, "failureOfEquipment")}
        if equipment_id not in targets:
            raise ValueError(f"FailureEvent {failure.id} is not scoped to equipment {equipment_id}")
        evidence.add(failure.id)
        status = _normalized_property(failure, "status")
        failure_modes = runtime.neighbors(failure.id, "hasFailureMode")
        evidence.update(item.id for item in failure_modes)

        if status in _CLOSED_STATUSES:
            continue
        if status not in _ACTIVE_FAILURE_STATUSES:
            raise ValueError(f"FailureEvent {failure.id} has unsupported status {status}")
        if not failure_modes:
            raise ValueError(f"Active FailureEvent {failure.id} has no FailureMode evidence")

        severity = _normalized_property(failure, "severity")
        band = _severity_band(severity)
        findings.append(
            ReliabilityFinding(
                code="failure.active",
                severity=band,
                message=f"Active failure event {failure.id} has severity {severity}",
                evidence_ids=[failure.id, *sorted(item.id for item in failure_modes)],
            )
        )

    return findings, evidence


def _assess_work_orders(
    runtime: CEPIORuntime,
    equipment_id: str,
    work_order_ids: list[str],
) -> tuple[list[ReliabilityFinding], set[str]]:
    linked = {item.id for item in runtime.neighbors(equipment_id, "hasWorkOrder")}
    findings: list[ReliabilityFinding] = []
    evidence: set[str] = set()

    for work_order_id in work_order_ids:
        work_order = _require_type(runtime, work_order_id, "WorkOrder")
        if work_order.id not in linked:
            raise ValueError(f"WorkOrder {work_order.id} is not linked to equipment {equipment_id}")
        evidence.add(work_order.id)
        status = _normalized_property(work_order, "status")

        if status in _CLOSED_STATUSES or status in {"CANCELLED", "CANCELED"}:
            continue
        if status in _BLOCKING_WORK_STATUSES:
            findings.append(
                ReliabilityFinding(
                    code="maintenance.work-blocked",
                    severity="blocking",
                    message=f"Maintenance work order {work_order.id} is {status}",
                    evidence_ids=[work_order.id],
                )
            )
            continue
        if status not in _ACTIVE_WORK_STATUSES:
            raise ValueError(f"WorkOrder {work_order.id} has unsupported status {status}")

        priority = _normalized_property(work_order, "priority")
        if priority in _NORMAL_PRIORITIES:
            continue
        if priority in _ADVISORY_PRIORITIES:
            findings.append(
                ReliabilityFinding(
                    code="maintenance.high-priority-work",
                    severity="advisory",
                    message=f"Active work order {work_order.id} has priority {priority}",
                    evidence_ids=[work_order.id],
                )
            )
        elif priority in _BLOCKING_PRIORITIES:
            findings.append(
                ReliabilityFinding(
                    code="maintenance.critical-work",
                    severity="blocking",
                    message=f"Active work order {work_order.id} has priority {priority}",
                    evidence_ids=[work_order.id],
                )
            )
        else:
            raise ValueError(f"WorkOrder {work_order.id} has unsupported priority {priority}")

    return findings, evidence


def _assess_risks(
    runtime: CEPIORuntime,
    equipment_id: str,
    risk_ids: list[str],
) -> tuple[list[ReliabilityFinding], set[str]]:
    linked = {item.id for item in runtime.neighbors(equipment_id, "hasRisk")}
    findings: list[ReliabilityFinding] = []
    evidence: set[str] = set()

    for risk_id in risk_ids:
        risk = _require_type(runtime, risk_id, "Risk")
        if risk.id not in linked:
            raise ValueError(f"Risk {risk.id} is not linked to equipment {equipment_id}")
        evidence.add(risk.id)
        status = _normalized_property(risk, "status")
        if status in _CLOSED_STATUSES:
            continue
        if status not in _ACTIVE_RISK_STATUSES:
            raise ValueError(f"Risk {risk.id} has unsupported status {status}")

        severity = _normalized_property(risk, "severity")
        band = _severity_band(severity)
        findings.append(
            ReliabilityFinding(
                code="risk.active",
                severity=band,
                message=f"Active reliability risk {risk.id} has severity {severity}",
                evidence_ids=[risk.id],
            )
        )

    return findings, evidence


def _recommended_action(findings: list[ReliabilityFinding]) -> str | None:
    blocking_codes = {item.code for item in findings if item.severity == "blocking"}
    advisory_codes = {item.code for item in findings if item.severity == "advisory"}

    if "risk.active" in blocking_codes:
        return "EscalateRisk"
    if "failure.active" in blocking_codes:
        return "CreateWorkOrder"
    if "condition.material-degradation" in blocking_codes:
        return "CreateInspection"
    if "condition.degraded" in advisory_codes or "failure.active" in advisory_codes:
        return "CreateInspection"
    if "risk.active" in advisory_codes:
        return "EscalateRisk"
    return None


def assess_asset_reliability(
    *,
    runtime: CEPIORuntime,
    equipment_id: str,
    assessment_time: datetime,
    condition_observation_ids: list[str],
    failure_event_ids: list[str] | None = None,
    work_order_ids: list[str] | None = None,
    risk_ids: list[str] | None = None,
) -> AssetReliabilityAssessment:
    """Assess reliability from current governed evidence without inventing a score."""

    if assessment_time.tzinfo is None:
        raise ValueError("assessment_time must include timezone context")
    equipment = _require_type(runtime, equipment_id, "Equipment")

    condition_findings, condition_evidence = _assess_condition(
        runtime, equipment.id, assessment_time, condition_observation_ids
    )
    failure_findings, failure_evidence = _assess_failures(
        runtime, equipment.id, list(failure_event_ids or [])
    )
    work_findings, work_evidence = _assess_work_orders(
        runtime, equipment.id, list(work_order_ids or [])
    )
    risk_findings, risk_evidence = _assess_risks(
        runtime, equipment.id, list(risk_ids or [])
    )
    findings = [*condition_findings, *failure_findings, *work_findings, *risk_findings]

    if any(item.severity == "blocking" for item in findings):
        status = AssetReliabilityStatus.intervention_required
    elif findings:
        status = AssetReliabilityStatus.degraded
    else:
        status = AssetReliabilityStatus.reliable

    action = _recommended_action(findings)
    if status == AssetReliabilityStatus.reliable:
        recommendation = "Current governed evidence supports continued service."
    elif action is not None:
        recommendation = (
            f"Reliability review is required; consider governed action {action} using the cited evidence."
        )
    else:
        recommendation = (
            "Reliability intervention is required, but v0.1 has no safe existing action mapping; "
            "route the evidence for human maintenance review."
        )

    evidence_ids = sorted(
        {
            equipment.id,
            *condition_evidence,
            *failure_evidence,
            *work_evidence,
            *risk_evidence,
        }
    )
    return AssetReliabilityAssessment(
        equipment_id=equipment.id,
        assessed_at=assessment_time,
        status=status,
        findings=findings,
        evidence_ids=evidence_ids,
        recommended_action=action,
        recommendation=recommendation,
    )


class ReliabilityAssetInterventionIndustryIQPack:
    pack_id = "cepio.iq.reliability.asset-intervention"
    version = "0.1.0"

    def install(self, runtime: CEPIORuntime) -> None:
        missing_actions = sorted(
            action for action in _REQUIRED_CORE_ACTIONS if not runtime.has_action(action)
        )
        if missing_actions:
            raise RuntimeError(
                "Reliability IQ requires governed Core actions: " + ", ".join(missing_actions)
            )
        if not runtime.has_decision(_REQUIRED_CORE_DECISION):
            raise RuntimeError(
                f"Reliability IQ requires Core decision {_REQUIRED_CORE_DECISION}"
            )
        runtime.register_function(
            "assessAssetReliability",
            assess_asset_reliability,
            input_model=AssetReliabilityInput,
            output_type=AssetReliabilityAssessment,
        )


RELIABILITY_ASSET_INTERVENTION_IQ_PACK = ReliabilityAssetInterventionIndustryIQPack()

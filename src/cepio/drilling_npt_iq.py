from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from pydantic import BaseModel, Field

from .model import ActionRequest, ObjectRef, OntologyObject, Relationship
from .runtime import CEPIORuntime


class NPTDurationInput(BaseModel):
    rig_id: str
    well_id: str
    activity_ids: list[str] = Field(min_length=1)


class NPTIntervalAssessment(BaseModel):
    activity_id: str
    duration_hours: float = Field(ge=0)
    productive: bool


class NPTDurationAssessment(BaseModel):
    rig_id: str
    well_id: str
    total_npt_hours: float = Field(ge=0)
    intervals: list[NPTIntervalAssessment]
    nonproductive_activity_ids: list[str]


def _is_a(runtime: CEPIORuntime, actual_type: str, expected_type: str) -> bool:
    if runtime.type_registry is None:
        return actual_type == expected_type
    return runtime.type_registry.is_a(actual_type, expected_type)


def _parse_timestamp(value: object, *, property_name: str, activity_id: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(
                f"Activity {activity_id} property {property_name} must be an ISO-8601 timestamp"
            ) from exc
    else:
        raise ValueError(
            f"Activity {activity_id} is missing required governed property {property_name}"
        )
    if parsed.tzinfo is None:
        raise ValueError(
            f"Activity {activity_id} property {property_name} must include timezone context"
        )
    return parsed


def _activity_productive(runtime: CEPIORuntime, activity_id: str) -> bool:
    classifications = runtime.neighbors(activity_id, "classifiedBy")
    if not classifications:
        raise ValueError(f"Activity {activity_id} has no governed DrillingActivityClassification")

    values: set[bool] = set()
    for classification in classifications:
        if not _is_a(runtime, classification.type, "DrillingActivityClassification"):
            raise ValueError(
                f"Activity {activity_id} classifiedBy target {classification.id} is not a DrillingActivityClassification"
            )
        value = classification.properties.get("isProductive")
        if not isinstance(value, bool):
            raise ValueError(
                f"Classification {classification.id} is missing normalized boolean isProductive"
            )
        values.add(value)

    if len(values) != 1:
        raise ValueError(f"Activity {activity_id} has conflicting productivity classifications")
    return next(iter(values))


def calculate_npt_duration(
    *,
    runtime: CEPIORuntime,
    rig_id: str,
    well_id: str,
    activity_ids: list[str],
) -> NPTDurationAssessment:
    """Derive NPT from governed activity/productivity evidence.

    The pack does not vendor IADC/WITSML codes and does not create an NPT event type.
    External classification codes remain source-owned; CEPIO consumes the normalized
    productivity meaning plus temporal/rig/well graph context.
    """

    rig = runtime.get_object(rig_id)
    well = runtime.get_object(well_id)
    if not _is_a(runtime, rig.type, "OperatingRig"):
        raise ValueError(f"{rig_id} is not an OperatingRig")
    if not _is_a(runtime, well.type, "Well"):
        raise ValueError(f"{well_id} is not a Well")

    intervals: list[NPTIntervalAssessment] = []
    nonproductive: list[str] = []
    total_hours = 0.0

    for activity_id in activity_ids:
        activity = runtime.get_object(activity_id)
        if not _is_a(runtime, activity.type, "ActivityInterval"):
            raise ValueError(f"{activity_id} is not an ActivityInterval")

        rig_ids = {item.id for item in runtime.neighbors(activity_id, "activityOnRig")}
        if rig_id not in rig_ids:
            raise ValueError(
                f"Activity {activity_id} is not linked to rig {rig_id} by activityOnRig"
            )
        well_ids = {item.id for item in runtime.neighbors(activity_id, "activityForWell")}
        if well_id not in well_ids:
            raise ValueError(
                f"Activity {activity_id} is not linked to well {well_id} by activityForWell"
            )

        start = _parse_timestamp(
            activity.properties.get("startTime"),
            property_name="startTime",
            activity_id=activity_id,
        )
        end = _parse_timestamp(
            activity.properties.get("endTime"),
            property_name="endTime",
            activity_id=activity_id,
        )
        if end < start:
            raise ValueError(f"Activity {activity_id} endTime precedes startTime")

        productive = _activity_productive(runtime, activity_id)
        duration_hours = (end - start).total_seconds() / 3600.0
        intervals.append(
            NPTIntervalAssessment(
                activity_id=activity_id,
                duration_hours=round(duration_hours, 6),
                productive=productive,
            )
        )
        if not productive:
            nonproductive.append(activity_id)
            total_hours += duration_hours

    return NPTDurationAssessment(
        rig_id=rig_id,
        well_id=well_id,
        total_npt_hours=round(total_hours, 6),
        intervals=intervals,
        nonproductive_activity_ids=nonproductive,
    )


def _require_activity_interval(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> tuple[bool, str]:
    return (
        _is_a(runtime, target.type, "ActivityInterval"),
        "Target must be an ActivityInterval",
    )


def _require_reason(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> tuple[bool, str]:
    return (
        bool(request.parameters.get("reason")),
        "Parameter reason is required",
    )


def create_npt_investigation(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> dict[str, object]:
    investigation_id = request.parameters.get(
        "investigation_id", f"NPT-INV-{uuid4().hex[:8].upper()}"
    )
    investigation = OntologyObject(
        id=str(investigation_id),
        type="NPTInvestigation",
        name=str(request.parameters.get("title", f"NPT investigation for {target.name}")),
        properties={
            "status": "open",
            "reason": request.parameters["reason"],
            "createdBy": request.actor_id,
            "sourceAction": request.action_type,
        },
        interfaces={"WorkItem"},
    )
    runtime.upsert_object(investigation)
    runtime.add_relationship(
        Relationship(
            type="investigatesActivity",
            source=ObjectRef(id=investigation.id, type=investigation.type),
            target=ObjectRef(id=target.id, type=target.type),
        )
    )
    return {
        "investigation_id": investigation.id,
        "activity_id": target.id,
        "external_side_effect": "not_configured",
    }


class DrillingNPTIndustryIQPack:
    pack_id = "cepio.iq.drilling.npt"
    version = "0.1.0"

    def install(self, runtime: CEPIORuntime) -> None:
        runtime.register_function(
            "calculateNPTDuration",
            calculate_npt_duration,
            input_model=NPTDurationInput,
            output_type=NPTDurationAssessment,
        )
        runtime.register_action(
            "CreateNPTInvestigation",
            create_npt_investigation,
            {"drilling_engineer", "drilling_superintendent", "rig_manager"},
            preconditions=[_require_activity_interval, _require_reason],
            requires_human_approval=True,
        )
        runtime.register_decision(
            "npt-follow-up-recommendation",
            allowed_subject_types={"ActivityInterval"},
            allowed_actions={"CreateNPTInvestigation", "CreateWorkOrder"},
        )


DRILLING_NPT_IQ_PACK = DrillingNPTIndustryIQPack()

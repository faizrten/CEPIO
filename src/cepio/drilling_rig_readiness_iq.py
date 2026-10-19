from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field

from .model import ActionRequest, ObjectRef, OntologyObject, Relationship
from .runtime import CEPIORuntime


class RigReadinessStatus(str, Enum):
    ready = "READY"
    conditionally_ready = "CONDITIONALLY_READY"
    not_ready = "NOT_READY"


class ReadinessDimension(str, Enum):
    equipment = "equipment"
    well_control = "well_control"
    workforce = "workforce"
    supply = "supply"


class ReadinessBlocker(BaseModel):
    dimension: ReadinessDimension
    code: str
    evidence_id: str
    severity: str
    message: str


class ReadinessDimensionAssessment(BaseModel):
    dimension: ReadinessDimension
    status: RigReadinessStatus
    evidence_ids: list[str]
    blocker_codes: list[str]


class RigReadinessInput(BaseModel):
    rig_id: str
    planned_activity_id: str
    assessment_time: datetime
    equipment_ids: list[str] = Field(default_factory=list)
    well_control_test_ids: list[str] = Field(default_factory=list)
    crew_assignment_ids: list[str] = Field(default_factory=list)
    material_requirement_ids: list[str] = Field(default_factory=list)
    inventory_position_ids: list[str] = Field(default_factory=list)
    required_dimensions: set[ReadinessDimension] = Field(
        default_factory=lambda: {
            ReadinessDimension.equipment,
            ReadinessDimension.well_control,
            ReadinessDimension.workforce,
            ReadinessDimension.supply,
        }
    )


class RigReadinessAssessment(BaseModel):
    rig_id: str
    planned_activity_id: str
    assessed_at: datetime
    status: RigReadinessStatus
    dimensions: list[ReadinessDimensionAssessment]
    blockers: list[ReadinessBlocker]
    evidence_ids: list[str]


def _is_a(runtime: CEPIORuntime, actual_type: str, expected_type: str) -> bool:
    if runtime.type_registry is None:
        return actual_type == expected_type
    return runtime.type_registry.is_a(actual_type, expected_type)


def _require_type(runtime: CEPIORuntime, object_id: str, expected_type: str) -> OntologyObject:
    obj = runtime.get_object(object_id)
    if not _is_a(runtime, obj.type, expected_type):
        raise ValueError(f"{object_id} is not a {expected_type}")
    return obj


def _normalized_status(obj: OntologyObject) -> str:
    value = obj.properties.get("status")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{obj.id} is missing required normalized status")
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


def _blocker(
    dimension: ReadinessDimension,
    code: str,
    evidence_id: str,
    message: str,
    *,
    advisory: bool = False,
) -> ReadinessBlocker:
    return ReadinessBlocker(
        dimension=dimension,
        code=code,
        evidence_id=evidence_id,
        severity="advisory" if advisory else "critical",
        message=message,
    )


def _dimension_result(
    dimension: ReadinessDimension,
    evidence_ids: set[str],
    blockers: list[ReadinessBlocker],
) -> ReadinessDimensionAssessment:
    relevant = [item for item in blockers if item.dimension == dimension]
    if any(item.severity == "critical" for item in relevant):
        status = RigReadinessStatus.not_ready
    elif relevant:
        status = RigReadinessStatus.conditionally_ready
    else:
        status = RigReadinessStatus.ready
    return ReadinessDimensionAssessment(
        dimension=dimension,
        status=status,
        evidence_ids=sorted(evidence_ids),
        blocker_codes=sorted(item.code for item in relevant),
    )


def _require_evidence_ids(
    required_dimensions: set[ReadinessDimension],
    dimension: ReadinessDimension,
    values: list[str],
) -> None:
    if dimension in required_dimensions and not values:
        raise ValueError(f"{dimension.value} readiness evidence is required")


def _assess_equipment(
    runtime: CEPIORuntime,
    equipment_ids: list[str],
) -> tuple[set[str], list[ReadinessBlocker]]:
    evidence: set[str] = set()
    blockers: list[ReadinessBlocker] = []
    ready = {"READY", "AVAILABLE", "IN_SERVICE", "OPERATIONAL"}
    conditional = {"CONDITIONAL", "CONDITIONALLY_READY", "DEGRADED"}
    active_work = {"OPEN", "BLOCKED", "OVERDUE", "IN_PROGRESS"}

    for equipment_id in equipment_ids:
        equipment = _require_type(runtime, equipment_id, "Equipment")
        evidence.add(equipment.id)
        status = _normalized_status(equipment)
        if status in conditional:
            blockers.append(
                _blocker(
                    ReadinessDimension.equipment,
                    "equipment.degraded",
                    equipment.id,
                    f"Equipment {equipment.id} is {status}",
                    advisory=True,
                )
            )
        elif status not in ready:
            blockers.append(
                _blocker(
                    ReadinessDimension.equipment,
                    "equipment.not-ready",
                    equipment.id,
                    f"Equipment {equipment.id} is {status}",
                )
            )

        for work_order in runtime.neighbors(equipment.id, "hasWorkOrder"):
            evidence.add(work_order.id)
            work_status = _normalized_status(work_order)
            if work_status not in active_work:
                continue
            readiness_blocking = work_order.properties.get("readinessBlocking")
            if not isinstance(readiness_blocking, bool):
                blockers.append(
                    _blocker(
                        ReadinessDimension.equipment,
                        "equipment.work-order-impact-unknown",
                        work_order.id,
                        f"Active work order {work_order.id} has no normalized readinessBlocking evidence",
                    )
                )
            elif readiness_blocking:
                blockers.append(
                    _blocker(
                        ReadinessDimension.equipment,
                        "equipment.blocking-work-order",
                        work_order.id,
                        f"Active work order {work_order.id} blocks rig readiness",
                    )
                )
    return evidence, blockers


def _assess_well_control(
    runtime: CEPIORuntime,
    test_ids: list[str],
    *,
    assessment_time: datetime,
) -> tuple[set[str], list[ReadinessBlocker]]:
    evidence: set[str] = set()
    blockers: list[ReadinessBlocker] = []
    passed = {"PASS", "PASSED", "VALID"}

    for test_id in test_ids:
        test = _require_type(runtime, test_id, "WellControlTest")
        evidence.add(test.id)
        status = _normalized_status(test)
        targets = runtime.neighbors(test.id, "testsWellControlEquipment")
        if not targets:
            blockers.append(
                _blocker(
                    ReadinessDimension.well_control,
                    "well-control.test-unscoped",
                    test.id,
                    f"Well-control test {test.id} is not linked to tested equipment",
                )
            )
        for target in targets:
            if not _is_a(runtime, target.type, "Equipment"):
                raise ValueError(f"Well-control test {test.id} target {target.id} is not Equipment")
            evidence.add(target.id)

        if status not in passed:
            blockers.append(
                _blocker(
                    ReadinessDimension.well_control,
                    "well-control.test-not-passed",
                    test.id,
                    f"Well-control test {test.id} is {status}",
                )
            )

        valid_to = test.properties.get("validTo")
        if valid_to is None:
            blockers.append(
                _blocker(
                    ReadinessDimension.well_control,
                    "well-control.validity-missing",
                    test.id,
                    f"Well-control test {test.id} has no validity horizon",
                )
            )
        else:
            expiry = _aware_datetime(valid_to, label=f"Well-control test {test.id} validTo")
            if expiry <= assessment_time:
                blockers.append(
                    _blocker(
                        ReadinessDimension.well_control,
                        "well-control.test-expired",
                        test.id,
                        f"Well-control test {test.id} expired before the readiness assessment",
                    )
                )
    return evidence, blockers


def _assess_workforce(
    runtime: CEPIORuntime,
    assignment_ids: list[str],
    *,
    planned_activity_id: str,
) -> tuple[set[str], list[ReadinessBlocker]]:
    evidence: set[str] = set()
    blockers: list[ReadinessBlocker] = []
    ready = {"READY", "ACTIVE", "CONFIRMED"}
    conditional = {"AT_RISK", "CONDITIONAL", "CONDITIONALLY_READY"}
    qualified = {"QUALIFIED", "COMPETENT", "MEETS_REQUIREMENT", "PASSED"}

    for assignment_id in assignment_ids:
        assignment = _require_type(runtime, assignment_id, "CrewAssignment")
        evidence.add(assignment.id)
        status = _normalized_status(assignment)
        if status in conditional:
            blockers.append(
                _blocker(
                    ReadinessDimension.workforce,
                    "workforce.assignment-at-risk",
                    assignment.id,
                    f"Crew assignment {assignment.id} is {status}",
                    advisory=True,
                )
            )
        elif status not in ready:
            blockers.append(
                _blocker(
                    ReadinessDimension.workforce,
                    "workforce.assignment-not-ready",
                    assignment.id,
                    f"Crew assignment {assignment.id} is {status}",
                )
            )

        activity_ids = {
            item.id for item in runtime.neighbors(assignment.id, "assignmentForActivity")
        }
        if planned_activity_id not in activity_ids:
            blockers.append(
                _blocker(
                    ReadinessDimension.workforce,
                    "workforce.assignment-wrong-activity",
                    assignment.id,
                    f"Crew assignment {assignment.id} is not scoped to {planned_activity_id}",
                )
            )

        people = runtime.neighbors(assignment.id, "assignmentOf")
        if not people:
            blockers.append(
                _blocker(
                    ReadinessDimension.workforce,
                    "workforce.assignment-unstaffed",
                    assignment.id,
                    f"Crew assignment {assignment.id} has no assigned crew member",
                )
            )
            continue
        assigned_person_ids = {person.id for person in people}
        evidence.update(assigned_person_ids)

        requirements = runtime.neighbors(assignment.id, "assignmentRequiresCompetency")
        if not requirements:
            blockers.append(
                _blocker(
                    ReadinessDimension.workforce,
                    "workforce.competency-requirement-missing",
                    assignment.id,
                    f"Crew assignment {assignment.id} has no competency requirement evidence",
                )
            )
            continue

        for requirement in requirements:
            evidence.add(requirement.id)
            assessments = runtime.reverse_neighbors(requirement.id, "assessmentAgainstRequirement")
            matched = False
            for assessment in assessments:
                if not _is_a(runtime, assessment.type, "CompetencyAssessment"):
                    continue
                evidence.add(assessment.id)
                assessed_people = {
                    person.id for person in runtime.neighbors(assessment.id, "assessmentOfPerson")
                }
                evidence.update(assessed_people)
                level = assessment.properties.get("competencyLevel")
                if (
                    assessed_people.intersection(assigned_person_ids)
                    and isinstance(level, str)
                    and level.strip().upper() in qualified
                ):
                    matched = True
                    break
            if not matched:
                blockers.append(
                    _blocker(
                        ReadinessDimension.workforce,
                        "workforce.competency-not-demonstrated",
                        requirement.id,
                        f"No qualifying competency assessment supports requirement {requirement.id}",
                    )
                )
    return evidence, blockers


def _as_number(value: object, *, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    return float(value)


def _assess_supply(
    runtime: CEPIORuntime,
    requirement_ids: list[str],
    inventory_ids: list[str],
    *,
    rig_id: str,
) -> tuple[set[str], list[ReadinessBlocker]]:
    evidence: set[str] = set()
    blockers: list[ReadinessBlocker] = []
    inventory_by_material: dict[str, list[OntologyObject]] = {}

    for inventory_id in inventory_ids:
        inventory = _require_type(runtime, inventory_id, "InventoryPosition")
        evidence.add(inventory.id)
        material_number = inventory.properties.get("materialNumber")
        if not isinstance(material_number, str) or not material_number.strip():
            raise ValueError(f"Inventory position {inventory.id} is missing materialNumber")
        inventory_by_material.setdefault(material_number.strip(), []).append(inventory)

    for requirement_id in requirement_ids:
        requirement = _require_type(runtime, requirement_id, "MaterialRequirement")
        evidence.add(requirement.id)
        status = _normalized_status(requirement)
        material_number = requirement.properties.get("materialNumber")
        if not isinstance(material_number, str) or not material_number.strip():
            raise ValueError(f"Material requirement {requirement.id} is missing materialNumber")
        material_number = material_number.strip()

        if status in {"AT_RISK", "CONDITIONAL", "CONDITIONALLY_READY"}:
            blockers.append(
                _blocker(
                    ReadinessDimension.supply,
                    "supply.requirement-at-risk",
                    requirement.id,
                    f"Material requirement {requirement.id} is {status}",
                    advisory=True,
                )
            )
        elif status not in {"READY", "SATISFIED", "AVAILABLE"}:
            blockers.append(
                _blocker(
                    ReadinessDimension.supply,
                    "supply.requirement-not-ready",
                    requirement.id,
                    f"Material requirement {requirement.id} is {status}",
                )
            )

        positions = inventory_by_material.get(material_number, [])
        if not positions:
            blockers.append(
                _blocker(
                    ReadinessDimension.supply,
                    "supply.inventory-missing",
                    requirement.id,
                    f"No inventory evidence is available for material {material_number}",
                )
            )
            continue

        material_ready = False
        for inventory in positions:
            evidence.add(inventory.id)
            stocked_assets = {
                asset.id for asset in runtime.neighbors(inventory.id, "stockedAtAsset")
            }
            on_hand = _as_number(
                inventory.properties.get("onHandQuantity"),
                label=f"Inventory position {inventory.id} onHandQuantity",
            )
            shortfall = _as_number(
                inventory.properties.get("shortfallQuantity"),
                label=f"Inventory position {inventory.id} shortfallQuantity",
            )
            if rig_id in stocked_assets and on_hand > 0 and shortfall <= 0:
                material_ready = True
                break
        if not material_ready:
            blockers.append(
                _blocker(
                    ReadinessDimension.supply,
                    "supply.stockout-or-wrong-location",
                    requirement.id,
                    f"Material {material_number} is not available without shortfall at rig {rig_id}",
                )
            )
    return evidence, blockers


def assess_rig_readiness(
    *,
    runtime: CEPIORuntime,
    rig_id: str,
    planned_activity_id: str,
    assessment_time: datetime,
    equipment_ids: list[str],
    well_control_test_ids: list[str],
    crew_assignment_ids: list[str],
    material_requirement_ids: list[str],
    inventory_position_ids: list[str],
    required_dimensions: set[ReadinessDimension],
) -> RigReadinessAssessment:
    """Derive rig readiness from cross-functional governed evidence.

    Readiness is intentionally an assessment, not a stored canonical rig flag. The
    function composes existing equipment, well-control, workforce and supply
    semantics and fails closed when a required evidence dimension is absent.
    """

    rig = _require_type(runtime, rig_id, "OperatingRig")
    planned_activity = _require_type(runtime, planned_activity_id, "ActivityInterval")
    assessed_at = _aware_datetime(assessment_time, label="assessment_time")
    if rig.id not in {item.id for item in runtime.neighbors(planned_activity.id, "activityOnRig")}:
        raise ValueError(f"Planned activity {planned_activity_id} is not linked to rig {rig_id}")

    _require_evidence_ids(required_dimensions, ReadinessDimension.equipment, equipment_ids)
    _require_evidence_ids(
        required_dimensions, ReadinessDimension.well_control, well_control_test_ids
    )
    _require_evidence_ids(required_dimensions, ReadinessDimension.workforce, crew_assignment_ids)
    _require_evidence_ids(required_dimensions, ReadinessDimension.supply, material_requirement_ids)
    if ReadinessDimension.supply in required_dimensions and not inventory_position_ids:
        raise ValueError("supply inventory readiness evidence is required")

    assessments: list[ReadinessDimensionAssessment] = []
    all_blockers: list[ReadinessBlocker] = []
    all_evidence: set[str] = {rig.id, planned_activity.id}

    evaluators = [
        (
            ReadinessDimension.equipment,
            lambda: _assess_equipment(runtime, equipment_ids),
        ),
        (
            ReadinessDimension.well_control,
            lambda: _assess_well_control(
                runtime, well_control_test_ids, assessment_time=assessed_at
            ),
        ),
        (
            ReadinessDimension.workforce,
            lambda: _assess_workforce(
                runtime,
                crew_assignment_ids,
                planned_activity_id=planned_activity_id,
            ),
        ),
        (
            ReadinessDimension.supply,
            lambda: _assess_supply(
                runtime,
                material_requirement_ids,
                inventory_position_ids,
                rig_id=rig_id,
            ),
        ),
    ]

    for dimension, evaluate in evaluators:
        if dimension not in required_dimensions:
            continue
        evidence, blockers = evaluate()
        all_evidence.update(evidence)
        all_blockers.extend(blockers)
        assessments.append(_dimension_result(dimension, evidence, blockers))

    if any(item.severity == "critical" for item in all_blockers):
        status = RigReadinessStatus.not_ready
    elif all_blockers:
        status = RigReadinessStatus.conditionally_ready
    else:
        status = RigReadinessStatus.ready

    return RigReadinessAssessment(
        rig_id=rig.id,
        planned_activity_id=planned_activity.id,
        assessed_at=assessed_at,
        status=status,
        dimensions=assessments,
        blockers=all_blockers,
        evidence_ids=sorted(all_evidence),
    )


def _require_operating_rig(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> tuple[bool, str]:
    return _is_a(runtime, target.type, "OperatingRig"), "Target must be an OperatingRig"


def _require_readiness_exception_context(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> tuple[bool, str]:
    reason = request.parameters.get("reason")
    planned_activity_id = request.parameters.get("planned_activity_id")
    blocker_codes = request.parameters.get("blocker_codes")
    valid = (
        isinstance(reason, str)
        and bool(reason.strip())
        and isinstance(planned_activity_id, str)
        and bool(planned_activity_id.strip())
        and isinstance(blocker_codes, list)
        and bool(blocker_codes)
    )
    return valid, "reason, planned_activity_id and non-empty blocker_codes are required"


def create_readiness_exception(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> dict[str, object]:
    exception_id = str(
        request.parameters.get("exception_id", f"RIG-READY-EXC-{uuid4().hex[:8].upper()}")
    )
    planned_activity_id = str(request.parameters["planned_activity_id"])
    planned_activity = _require_type(runtime, planned_activity_id, "ActivityInterval")
    exception = OntologyObject(
        id=exception_id,
        type="WorkItem",
        name=str(request.parameters.get("title", f"Rig readiness exception for {target.name}")),
        properties={
            "status": "OPEN",
            "workItemKind": "rig-readiness-exception",
            "reason": request.parameters["reason"],
            "blockerCodes": list(request.parameters["blocker_codes"]),
            "createdBy": request.actor_id,
            "sourceAction": request.action_type,
        },
    )
    runtime.upsert_object(exception)
    runtime.add_relationship(
        Relationship(
            type="impacts",
            source=ObjectRef(id=exception.id, type=exception.type),
            target=ObjectRef(id=target.id, type=target.type),
        )
    )
    runtime.add_relationship(
        Relationship(
            type="dependsOn",
            source=ObjectRef(id=exception.id, type=exception.type),
            target=ObjectRef(id=planned_activity.id, type=planned_activity.type),
        )
    )
    return {
        "readiness_exception_id": exception.id,
        "rig_id": target.id,
        "planned_activity_id": planned_activity.id,
        "external_side_effect": "not_configured",
    }


class DrillingRigReadinessIndustryIQPack:
    pack_id = "cepio.iq.drilling.rig-readiness"
    version = "0.1.0"

    def install(self, runtime: CEPIORuntime) -> None:
        runtime.register_function(
            "assessRigReadiness",
            assess_rig_readiness,
            input_model=RigReadinessInput,
            output_type=RigReadinessAssessment,
        )
        runtime.register_action(
            "CreateReadinessException",
            create_readiness_exception,
            {"rig_manager", "drilling_superintendent", "offshore_installation_manager"},
            preconditions=[_require_operating_rig, _require_readiness_exception_context],
            requires_human_approval=True,
        )
        runtime.register_decision(
            "rig-readiness-intervention-recommendation",
            allowed_subject_types={"OperatingRig"},
            allowed_actions={
                "CreateReadinessException",
                "CreateWorkOrder",
                "CreateInspection",
                "RequestCompetencyVerification",
                "CreateMaterialExpediteRequest",
            },
        )


DRILLING_RIG_READINESS_IQ_PACK = DrillingRigReadinessIndustryIQPack()

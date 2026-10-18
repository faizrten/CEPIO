from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from .model import ActionRequest, ObjectRef, OntologyObject, Relationship
from .runtime import CEPIORuntime


def require_interface(interface: str):
    def _check(
        request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
    ) -> tuple[bool, str]:
        return (interface in target.interfaces, f"Target must implement interface {interface}")

    return _check


def require_target_type(*types: str):
    allowed = set(types)

    def _check(
        request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
    ) -> tuple[bool, str]:
        return (target.type in allowed, f"Target type must be one of {sorted(allowed)}")

    return _check


def require_parameter(name: str):
    def _check(
        request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
    ) -> tuple[bool, str]:
        return (
            name in request.parameters and request.parameters[name] not in (None, ""),
            f"Parameter {name} is required",
        )

    return _check


def create_work_order(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> dict:
    wo_id = request.parameters.get("work_order_id", f"WO-{uuid4().hex[:8].upper()}")
    work_order = OntologyObject(
        id=wo_id,
        type="WorkOrder",
        name=request.parameters.get("title", f"Work order for {target.name}"),
        properties={
            "status": "created",
            "priority": request.parameters.get("priority", "medium"),
            "createdBy": request.actor_id,
            "sourceAction": request.action_type,
        },
        interfaces={"WorkItem"},
    )
    runtime.upsert_object(work_order)
    runtime.add_relationship(
        Relationship(
            type="hasWorkOrder",
            source=ObjectRef(id=target.id, type=target.type),
            target=ObjectRef(id=work_order.id, type=work_order.type),
        )
    )
    spare_id = request.parameters.get("spare_id")
    if spare_id:
        spare = runtime.get_object(spare_id)
        runtime.add_relationship(
            Relationship(
                type="requiresSpare",
                source=ObjectRef(id=work_order.id, type=work_order.type),
                target=ObjectRef(id=spare.id, type=spare.type),
            )
        )
    return {
        "work_order_id": wo_id,
        "spare_id": spare_id,
        "external_side_effect": "not_configured",
    }


def create_inspection(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> dict:
    inspection_id = request.parameters.get(
        "inspection_id", f"INSP-{uuid4().hex[:8].upper()}"
    )
    inspection = OntologyObject(
        id=inspection_id,
        type="Inspection",
        name=request.parameters.get("title", f"Inspection of {target.name}"),
        properties={
            "status": "planned",
            "requestedBy": request.actor_id,
            "sourceAction": request.action_type,
        },
        interfaces={"WorkItem"},
    )
    runtime.upsert_object(inspection)
    runtime.add_relationship(
        Relationship(
            type="hasInspection",
            source=ObjectRef(id=target.id, type=target.type),
            target=ObjectRef(id=inspection.id, type=inspection.type),
        )
    )
    return {"inspection_id": inspection_id, "external_side_effect": "not_configured"}


def escalate_risk(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> dict:
    prior = target.properties.get("riskStatus")
    expected = target.version
    target.properties["riskStatus"] = request.parameters.get("risk_status", "escalated")
    target.properties["riskEscalatedAt"] = datetime.now(timezone.utc).isoformat()
    stored = runtime.upsert_object(target, expected_version=expected)
    return {
        "previous_risk_status": prior,
        "risk_status": stored.properties["riskStatus"],
        "object_version": stored.version,
    }


def defer_work_order(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> dict:
    """Apply an approved maintenance deferral to a WorkOrder.

    Authorization and human-approval requirements are enforced by the runtime/policy
    definition. The handler only applies the governed state transition.
    """
    expected = target.version
    prior = target.properties.get("status")
    target.properties["status"] = "deferred"
    target.properties["deferralReason"] = request.parameters["reason"]
    target.properties["deferredUntil"] = request.parameters["until"]
    target.properties["approvedBy"] = request.actor_id
    stored = runtime.upsert_object(target, expected_version=expected)
    return {
        "previous_status": prior,
        "status": stored.properties["status"],
        "deferred_until": stored.properties["deferredUntil"],
        "object_version": stored.version,
    }


def approve_maintenance_deferral(
    request: ActionRequest, target: OntologyObject, runtime: CEPIORuntime
) -> dict:
    """Backward-compatible combined approval/application action.

    New Skill bindings use ``DeferWorkOrder`` so approval policy and the state-changing
    execution primitive are named separately. This legacy action remains behaviorally
    unchanged for existing callers.
    """
    return defer_work_order(request, target, runtime)


def restore_risk_status(
    request: ActionRequest, target: OntologyObject, effects: dict, runtime: CEPIORuntime
) -> dict:
    expected = target.version
    target.properties["riskStatus"] = effects.get("previous_risk_status")
    stored = runtime.upsert_object(target, expected_version=expected)
    return {
        "risk_status": stored.properties.get("riskStatus"),
        "object_version": stored.version,
    }

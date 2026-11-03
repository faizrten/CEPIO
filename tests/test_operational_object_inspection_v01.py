from __future__ import annotations

import json

import pytest

from cepio.application_contract import CEPIOApplicationService, ExecutionContext
from cepio.bootstrap import build_runtime
from cepio.model import ObjectRef, OntologyObject, Relationship
from cepio.operational_object_inspection import inspect_operational_object
from cepio.policy import RolePolicyEngine
from cepio.runtime import AuthorizationError


def fixture_service():
    runtime = build_runtime(validate_types=False, validate_properties=False)
    runtime.policy_engine = RolePolicyEngine(
        {
            "viewer": {
                "read_types": ["Compressor", "WorkOrder"],
                "read_scopes": ["public"],
                "read_properties": {
                    "Compressor": ["criticality"],
                    "WorkOrder": ["status"],
                },
            },
            "outsider": {"read_types": []},
        }
    )
    objects = [
        OntologyObject(
            id="K-201",
            type="Compressor",
            name="K-201",
            properties={
                "criticality": "high",
                "operatingState": "degraded",
                "sharingScope": "public",
            },
        ),
        OntologyObject(
            id="WO-1",
            type="WorkOrder",
            name="Inspection",
            properties={
                "status": "planned",
                "internalComment": "private",
                "sharingScope": "public",
            },
        ),
        OntologyObject(
            id="WO-SECRET",
            type="WorkOrder",
            name="Restricted work",
            properties={"status": "hold", "sharingScope": "restricted"},
        ),
        OntologyObject(id="UNIT-1", type="Hydrocracker", name="Unit"),
    ]
    for obj in objects:
        runtime.upsert_object(obj)
    for rel_type, source, target in (
        ("hasWorkOrder", "K-201", "WO-1"),
        ("hasWorkOrder", "K-201", "WO-SECRET"),
        ("contains", "UNIT-1", "K-201"),
    ):
        ids = {obj.id: obj for obj in objects}
        runtime.add_relationship(
            Relationship(
                type=rel_type,
                source=ObjectRef(id=source, type=ids[source].type),
                target=ObjectRef(id=target, type=ids[target].type),
            )
        )
    return runtime, CEPIOApplicationService(runtime)


def test_snapshot_reuses_actor_scoped_reads_and_hides_restricted_neighbors():
    runtime, service = fixture_service()
    context = ExecutionContext(
        actor_id="trusted-host-viewer",
        actor_roles=frozenset({"viewer"}),
        correlation_id="corr-k201",
    )
    snapshot = inspect_operational_object(service, "K-201", context)
    assert snapshot.context.subject.id == "K-201"
    assert snapshot.context.subject.properties == {"criticality": "high"}
    assert snapshot.context.metadata.correlation_id == "corr-k201"
    assert [obj.id for obj in snapshot.context.related_objects] == ["WO-1"]
    assert snapshot.context.related_objects[0].properties == {"status": "planned"}
    assert [link.related.id for link in snapshot.links] == ["WO-1"]
    assert snapshot.links[0].relationship_type == "hasWorkOrder"
    payload = json.dumps(snapshot.model_dump(mode="json"), sort_keys=True)
    assert "WO-SECRET" not in payload
    assert "UNIT-1" not in payload
    assert "internalComment" not in payload
    assert "operatingState" not in payload
    assert snapshot.state_qualification == "not_live_qualified"
    assert snapshot.evidence_qualification == "not_attested"
    assert snapshot.action_qualification == "not_evaluated"
    assert runtime.all_audits() == []
    assert runtime.list_decisions() == []


def test_subject_access_is_mandatory_and_no_neighbor_path_bypasses_it():
    _, service = fixture_service()
    with pytest.raises(AuthorizationError):
        inspect_operational_object(
            service,
            "K-201",
            ExecutionContext(actor_id="unprivileged", actor_roles=frozenset({"outsider"})),
        )
    with pytest.raises(KeyError):
        inspect_operational_object(
            service,
            "NOT-FOUND",
            ExecutionContext(actor_id="viewer", actor_roles=frozenset({"viewer"})),
        )


@pytest.mark.parametrize("max_related", [0, -1, 51])
def test_related_limit_is_bounded(max_related):
    _, service = fixture_service()
    with pytest.raises(ValueError, match="max_related"):
        inspect_operational_object(
            service,
            "K-201",
            ExecutionContext(actor_id="viewer", actor_roles=frozenset({"viewer"})),
            max_related=max_related,
        )


def test_restricted_subject_does_not_become_visible_through_inspection():
    _, service = fixture_service()
    with pytest.raises(AuthorizationError):
        inspect_operational_object(
            service,
            "WO-SECRET",
            ExecutionContext(actor_id="viewer", actor_roles=frozenset({"viewer"})),
        )


def test_max_related_limits_serialized_link_references():
    runtime, service = fixture_service()
    runtime.upsert_object(
        OntologyObject(
            id="WO-2",
            type="WorkOrder",
            name="Second work order",
            properties={"status": "planned", "sharingScope": "public"},
        )
    )
    runtime.add_relationship(
        Relationship(
            type="hasWorkOrder",
            source=ObjectRef(id="K-201", type="Compressor"),
            target=ObjectRef(id="WO-2", type="WorkOrder"),
        )
    )
    snapshot = inspect_operational_object(
        service,
        "K-201",
        ExecutionContext(actor_id="viewer", actor_roles=frozenset({"viewer"})),
        max_related=1,
    )
    assert len(snapshot.links) == 1
    assert len(snapshot.context.related_objects) == 1


def test_inspection_rejects_relationship_endpoint_type_mismatch(monkeypatch):
    runtime, service = fixture_service()
    bad = Relationship(
        type="hasWorkOrder",
        source=ObjectRef(id="K-201", type="Pump"),
        target=ObjectRef(id="WO-1", type="WorkOrder"),
    )
    monkeypatch.setattr(
        runtime.object_repository,
        "get_relationships",
        lambda object_id, direction: [bad] if direction == "out" else [],
    )
    with pytest.raises(ValueError, match="subject type"):
        inspect_operational_object(
            service,
            "K-201",
            ExecutionContext(actor_id="viewer", actor_roles=frozenset({"viewer"})),
        )


def test_inspection_rejects_related_reference_type_mismatch(monkeypatch):
    runtime, service = fixture_service()
    bad = Relationship(
        type="hasWorkOrder",
        source=ObjectRef(id="K-201", type="Compressor"),
        target=ObjectRef(id="WO-1", type="Pump"),
    )
    monkeypatch.setattr(
        runtime.object_repository,
        "get_relationships",
        lambda object_id, direction: [bad] if direction == "out" else [],
    )
    with pytest.raises(ValueError, match="related object type"):
        inspect_operational_object(
            service,
            "K-201",
            ExecutionContext(actor_id="viewer", actor_roles=frozenset({"viewer"})),
        )


def test_inspection_rejects_oversized_relationship_scan(monkeypatch):
    runtime, service = fixture_service()
    valid = Relationship(
        type="hasWorkOrder",
        source=ObjectRef(id="K-201", type="Compressor"),
        target=ObjectRef(id="WO-1", type="WorkOrder"),
    )
    monkeypatch.setattr(
        runtime.object_repository,
        "get_relationships",
        lambda object_id, direction: [valid] * 501 if direction == "out" else [],
    )
    with pytest.raises(ValueError, match="scan budget exceeded"):
        inspect_operational_object(
            service,
            "K-201",
            ExecutionContext(actor_id="viewer", actor_roles=frozenset({"viewer"})),
        )

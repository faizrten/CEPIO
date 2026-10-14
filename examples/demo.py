import json
from pathlib import Path

from cepio.bootstrap import build_runtime
from cepio.model import ActionRequest, Decision, ObjectRef, OntologyObject, OperationalEvent, Relationship

runtime = build_runtime()
data = json.loads((Path(__file__).parent / "satorp_hydrocracker.json").read_text())

for raw in data["objects"]:
    runtime.upsert_object(OntologyObject.model_validate(raw))
for raw in data["relationships"]:
    runtime.add_relationship(Relationship.model_validate(raw))
for raw in data["events"]:
    runtime.record_event(OperationalEvent.model_validate(raw))

risk = runtime.call_function("calculateAssetRisk", asset_id="K-201")
loss = runtime.call_function("calculateProductionLoss", asset_id="K-201", hours=4.7, unit_margin_per_hour=42000)

decision = runtime.save_decision(
    Decision(
        subject=ObjectRef(id="K-201", type="Compressor"),
        problem="Hydrocracker margin degradation associated with recycle-gas compressor trips",
        observations=["Two recent trips", f"Calculated asset risk={risk}"],
        recommendation="Inspect K-201 bearings and secure the critical bearing cartridge",
        recommended_action="CreateWorkOrder",
        confidence=0.88,
        created_by="cepio-reliability-agent",
    )
)

result = runtime.execute_action(
    ActionRequest(
        action_type="CreateWorkOrder",
        target=ObjectRef(id="K-201", type="Compressor"),
        actor_id="engineer@example",
        actor_roles={"maintenance_engineer"},
        parameters={"title": "Inspect K-201 bearings", "priority": "high", "work_order_id": "WO-K201-001", "spare_id": "SPARE-BRG-201"},
        idempotency_key="K201-bearing-response-v1",
        decision_id=decision.id,
    )
)

unit = runtime.traverse("KPI-MARGIN", ["^measuredBy"])[0]
compressor_obj = runtime.traverse(unit.id, ["contains"])[0]
work_order = runtime.traverse(compressor_obj.id, ["hasWorkOrder"])[0]
spare = runtime.traverse(work_order.id, ["requiresSpare"])[0]
supplier = runtime.traverse(spare.id, ["suppliedBy"])[0]

print("CEPIO v0.2 cross-domain reasoning chain")
print("KPI:", runtime.get_object("KPI-MARGIN").name)
print("Process unit:", unit.name)
print("Asset:", compressor_obj.name)
print("Events:", [event.type for event in runtime.events_for(compressor_obj.id)])
print("Calculated risk:", risk)
print("Estimated production-margin loss USD:", loss)
print("Decision:", decision.recommendation)
print("Action status:", result.status.value)
print("Work order:", work_order.id)
print("Required spare:", spare.name, "stockOnHand=", spare.properties["stockOnHand"])
print("Supplier:", supplier.name)
print("Audit entries:", len(runtime.all_audits()))

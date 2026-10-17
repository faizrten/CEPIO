from __future__ import annotations

from cepio.bootstrap import build_runtime
from cepio.skill_preflight import (
    SkillAuthorityContract,
    SkillGraphPathRequirement,
    SkillGraphPathStep,
    SkillPreflightSpec,
    SkillRegistry,
    evaluate_skill_preflight,
)


CORE = "https://cepio.org/ontology/core#"
IND = "https://cepio.org/ontology/industrial#"
REL = "https://cepio.org/ontology/reliability#"
PERF = "https://cepio.org/ontology/performance#"


def equipment_skill_spec() -> SkillPreflightSpec:
    return SkillPreflightSpec(
        skill_id="cepio.skill.reliability.investigate-equipment-degradation",
        binding_id="test-binding",
        object_types={
            "Asset": CORE + "Asset",
            "Equipment": IND + "Equipment",
            "ConditionObservation": REL + "ConditionObservation",
            "WorkOrder": IND + "WorkOrder",
            "FailureEvent": REL + "FailureEvent",
            "FailureMode": REL + "FailureMode",
            "ProductionExposure": PERF + "ProductionExposure",
        },
        relationships={
            "hasConditionObservation": REL + "hasConditionObservation",
            "hasWorkOrder": IND + "hasWorkOrder",
            "failureOfEquipment": REL + "failureOfEquipment",
            "hasFailureMode": REL + "hasFailureMode",
        },
        functions={"calculate-production-exposure": "calculateProductionExposure"},
        decisions={
            "maintenance-intervention-recommendation": "maintenance-intervention-recommendation"
        },
        actions={"create-work-order": "CreateWorkOrder"},
        evidence_types={
            "Equipment",
            "ConditionObservation",
            "WorkOrder",
            "FailureEvent",
            "FailureMode",
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
                id="maintenance-history",
                start_type="Equipment",
                steps=[
                    SkillGraphPathStep(
                        relationship="hasWorkOrder",
                        target_type="WorkOrder",
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
            approval_required_for={"create-work-order"},
        ),
    )


def test_recommender_is_ready_for_first_bound_skill():
    runtime = build_runtime()
    result = evaluate_skill_preflight(
        runtime,
        equipment_skill_spec(),
        actor_id="skill-agent-1",
        actor_roles={"ai_agent_recommender"},
    )

    assert result.status == "READY"
    assert result.blockers == []
    assert any(check.code == "GRAPH_PATH_REACHABLE" for check in result.checks)
    assert any(check.code == "ACTION_HANDOFF_ENFORCED" for check in result.checks)
    assert any(check.code == "DECISION_ACTION_AUDITABLE" for check in result.checks)


def test_auditor_is_blocked_by_runtime_policy_not_identifier_availability():
    runtime = build_runtime()
    result = evaluate_skill_preflight(
        runtime,
        equipment_skill_spec(),
        actor_id="audit-1",
        actor_roles={"auditor"},
    )

    assert result.status == "BLOCKED"
    codes = {check.code for check in result.blockers}
    assert "FUNCTION_NOT_AUTHORIZED" in codes
    assert "DECISION_NOT_AUTHORIZED" in codes
    assert "ACTION_NOT_RECOMMENDABLE" in codes


def test_over_authorized_actor_is_blocked_for_recommend_only_skill():
    runtime = build_runtime()
    result = evaluate_skill_preflight(
        runtime,
        equipment_skill_spec(),
        actor_id="maint-1",
        actor_roles={"maintenance_engineer"},
    )

    assert result.status == "BLOCKED"
    assert any(check.code == "ACTOR_EXCEEDS_SKILL_AUTHORITY" for check in result.blockers)


def test_invalid_semantic_shortcut_path_is_blocked():
    runtime = build_runtime()
    spec = equipment_skill_spec()
    spec.graph_paths = [
        SkillGraphPathRequirement(
            id="invalid-direct-failure-mode",
            start_type="Equipment",
            steps=[
                SkillGraphPathStep(
                    relationship="hasFailureMode",
                    target_type="FailureMode",
                )
            ],
        )
    ]

    result = evaluate_skill_preflight(
        runtime,
        spec,
        actor_id="skill-agent-1",
        actor_roles={"ai_agent_recommender"},
    )

    assert result.status == "BLOCKED"
    assert any(check.code == "GRAPH_PATH_INVALID" for check in result.blockers)


def test_unbound_evidence_dependency_fails_closed():
    runtime = build_runtime()
    spec = equipment_skill_spec()
    spec.evidence_types.add("InspectionEvidence")

    result = evaluate_skill_preflight(
        runtime,
        spec,
        actor_id="skill-agent-1",
        actor_roles={"ai_agent_recommender"},
    )

    assert result.status == "BLOCKED"
    assert any(check.code == "EVIDENCE_TYPE_NOT_BOUND" for check in result.blockers)


def test_skill_registry_rechecks_actor_at_preflight_time():
    runtime = build_runtime()
    registry = SkillRegistry(runtime)
    registry.register(equipment_skill_spec())

    ready = registry.preflight(
        "cepio.skill.reliability.investigate-equipment-degradation",
        actor_id="skill-agent-1",
        actor_roles={"ai_agent_recommender"},
    )
    blocked = registry.preflight(
        "cepio.skill.reliability.investigate-equipment-degradation",
        actor_id="audit-1",
        actor_roles={"auditor"},
    )

    assert ready.status == "READY"
    assert blocked.status == "BLOCKED"

#!/usr/bin/env python3
"""Qualify the synthetic refinery operating abstraction and K-201 governed-action loop.

This runner is deliberately deterministic. It proves CEPIO runtime composition,
evidence grounding and governed execution over synthetic/source-neutral fixtures. It is
not a substitute for the live PI/SAP qualification required by the CEPIO v0.5 gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cepio import (
    ExternalActionBinding,
    ExternalIdentityMapping,
    IdentityReconciliationStatus,
    PolicyCondition,
    PolicyConditionOperator,
    PolicyDefinition,
    PolicyObligation,
    PolicyObligationKind,
    PolicyRegistry,
    PolicyRule,
    WorkflowDefinition,
    WorkflowOutcomeStatus,
    WorkflowPolicyBoundary,
    WorkflowStatus,
    WorkflowStepDefinition,
    WorkflowStepType,
    build_external_action_runtime,
    build_external_kinetic_runtime,
)
from cepio.adapters import FakeGovernedWriteAdapter
from cepio.bootstrap import build_runtime
from cepio.model import ActionRequest, ObjectRef, OntologyObject, PolicyEffect
from cepio.runtime import AuthorizationError
from cepio.runtime_coverage import run_runtime_coverage


def _policy() -> PolicyDefinition:
    return PolicyDefinition(
        id="k201-high-risk-maintenance-approval",
        version="1.0.0",
        rules=(
            PolicyRule(
                id="high-risk-k201",
                effect=PolicyEffect.approval_required,
                conditions=(
                    PolicyCondition(
                        path="context.criticality",
                        operator=PolicyConditionOperator.eq,
                        value="safety_critical",
                    ),
                    PolicyCondition(
                        path="context.risk_score",
                        operator=PolicyConditionOperator.gte,
                        value=0.7,
                    ),
                ),
                obligations=(
                    PolicyObligation(
                        kind=PolicyObligationKind.require_approval_authority,
                        parameters={"role": "maintenance_manager"},
                    ),
                    PolicyObligation(kind=PolicyObligationKind.require_evidence),
                    PolicyObligation(kind=PolicyObligationKind.require_decision_record),
                ),
            ),
        ),
        default_effect=PolicyEffect.allow,
    )


def _workflow(policy: PolicyDefinition) -> WorkflowDefinition:
    return WorkflowDefinition(
        id="k201-governed-maintenance",
        name="K-201 governed maintenance intervention",
        version="0.1.0",
        policy_references=(policy.reference,),
        steps=[
            WorkflowStepDefinition(
                id="decision",
                type=WorkflowStepType.decision,
                decision_problem="Does K-201 require governed maintenance work?",
                decision_recommendation="Create a high-priority work order for K-201 bearing inspection.",
                recommended_action="CreateWorkOrder",
            ),
            WorkflowStepDefinition(
                id="create-work-order",
                type=WorkflowStepType.action,
                operation="CreateWorkOrder",
                parameters={"priority": "high", "title": "Inspect K-201 bearings"},
            ),
            WorkflowStepDefinition(
                id="verify-external",
                type=WorkflowStepType.external_verification,
                action_step_id="create-work-order",
            ),
        ],
    )


def run_k201_lighthouse_gate() -> dict[str, Any]:
    runtime = build_runtime()
    target = runtime.upsert_object(
        OntologyObject(
            id="K-201",
            type="Compressor",
            name="Recycle Gas Compressor K-201",
            properties={"criticality": "safety_critical", "risk_score": 0.82},
            interfaces={"MaintainableAsset", "Inspectable", "RiskBearing"},
        )
    )

    agent_denied = False
    try:
        runtime.execute_action(
            ActionRequest(
                action_type="CreateWorkOrder",
                target=ObjectRef(id=target.id, type=target.type),
                actor_id="operator-agent-direct",
                actor_roles={"ai_agent_recommender"},
                parameters={"priority": "high"},
                idempotency_key="k201-direct-agent-write",
            )
        )
    except AuthorizationError:
        agent_denied = True

    external = build_external_action_runtime(runtime)
    adapter = FakeGovernedWriteAdapter("synthetic_sap")
    external.register_adapter(adapter)
    external.register_binding(
        ExternalActionBinding(
            action_type="CreateWorkOrder",
            system="synthetic_sap",
            operation="create_work_order",
            identity_type="equipment",
        )
    )
    external.register_identity(
        ExternalIdentityMapping(
            cepio_object_id="K-201",
            system="synthetic_sap",
            identity_type="equipment",
            external_id="SAP-EQ-K201",
            status=IdentityReconciliationStatus.verified,
        )
    )

    policy = _policy()
    kinetic = build_external_kinetic_runtime(runtime, external)
    kinetic.workflow_policy = WorkflowPolicyBoundary(PolicyRegistry([policy]))
    kinetic.register_workflow(_workflow(policy))

    paused = kinetic.start_workflow(
        "k201-governed-maintenance",
        subject=ObjectRef(id="K-201", type="Compressor"),
        actor_id="reliability-copilot",
        actor_roles={"maintenance_engineer", "ai_agent_recommender"},
        trigger_key="condition:K-201:bearing-vibration-high",
    )
    approval = kinetic.pending_approval(paused.id)

    ai_approval_denied = False
    if approval is not None:
        try:
            kinetic.decide_approval(
                approval.id,
                actor_id="reliability-copilot",
                actor_roles={"ai_agent", "maintenance_engineer"},
                approved=True,
            )
        except PermissionError:
            ai_approval_denied = True

    if approval is None:
        waiting = paused
    else:
        waiting = kinetic.decide_approval(
            approval.id,
            actor_id="maintenance-manager-1",
            actor_roles={"maintenance_manager", "maintenance_engineer"},
            approved=True,
        )

    kinetic.tick_external_verification(waiting.id)
    completed = kinetic.tick_external_verification(waiting.id)
    replay = kinetic.tick_external_verification(waiting.id)

    action_id = completed.step_states["create-work-order"].action_id
    audits = runtime.audits_for_action(action_id) if action_id else []
    outcomes = kinetic.outcomes(completed.id)
    outcome = outcomes[0] if outcomes else None
    policy_evidence = audits[0].policy_evidence if audits else {}

    checks = {
        "direct_agent_write_denied": agent_denied,
        "policy_paused_for_human_approval": paused.status == WorkflowStatus.waiting_for_approval,
        "ai_cannot_self_approve": ai_approval_denied,
        "external_write_waits_for_verification": waiting.status
        == WorkflowStatus.waiting_for_external_verification,
        "workflow_completed": completed.status == WorkflowStatus.completed,
        "external_write_exactly_once": len(adapter.write_calls) == 1,
        "external_verification_exactly_once": len(adapter.verify_calls) == 1,
        "replay_is_idempotent": replay.status == WorkflowStatus.completed
        and len(adapter.write_calls) == 1,
        "policy_evidence_audited": bool(policy_evidence)
        and policy_evidence.get("evaluation", {}).get("matched_rules") == ["high-risk-k201"],
        "verified_workflow_outcome": outcome is not None
        and outcome.status == WorkflowOutcomeStatus.verified,
    }
    passed = all(checks.values())
    return {
        "gate": "k201-governed-action-lighthouse",
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "workflow_instance_id": completed.id,
        "action_id": action_id,
        "external_execution_id": completed.step_states["verify-external"].external_execution_id,
        "outcome_id": outcome.id if outcome else None,
        "policy_reference": policy.reference,
        "policy_evidence": policy_evidence,
        "synthetic_adapter": "synthetic_sap",
        "live_source_qualified": False,
    }


def run_qualification(repo_root: Path, suite_path: Path) -> dict[str, Any]:
    runtime_report = run_runtime_coverage(repo_root, suite_path)
    lighthouse = run_k201_lighthouse_gate()
    runtime_pass = runtime_report["status_counts"]["PASS"] == runtime_report["question_count"]
    passed = runtime_pass and lighthouse["status"] == "PASS"
    return {
        "qualification_version": "0.1",
        "mode": "deterministic-refinery-operating-abstraction-qualification",
        "status": "PASS" if passed else "FAIL",
        "runtime_evidence": runtime_report,
        "lighthouse": lighthouse,
        "live_integration_claim": False,
        "release_gate_note": (
            "This synthetic qualification is a prerequisite for, not completion of, the CEPIO v0.5 live industrial integration gate."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run refinery operating-abstraction qualification")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--suite",
        type=Path,
        default=Path("generalization/runtime/refinery-operating-abstraction-v0.1.yaml"),
    )
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-gap", action="store_true")
    args = parser.parse_args()

    root = args.repo_root.resolve()
    suite = args.suite if args.suite.is_absolute() else root / args.suite
    report = run_qualification(root, suite)

    runtime = report["runtime_evidence"]
    print("CEPIO Refinery Operating Abstraction Qualification v0.1")
    print(f"status: {report['status']}")
    print(f"runtime questions: {runtime['question_count']}")
    print(f"runtime status: {runtime['status_counts']}")
    print(f"runtime evidence coverage: {runtime['runtime_coverage_rate']:.1%}")
    print(f"K-201 lighthouse: {report['lighthouse']['status']}")
    for name, passed in report["lighthouse"]["checks"].items():
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")
    print("live source qualified: false")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8"
        )

    if args.fail_on_gap and report["status"] != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the CEPIO compounding industrial-intelligence control loop."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

from cepio.capability_registry import (
    CapabilityRegistry,
    HumanDecision,
    PromotionCandidate,
    PromotionDecisionValue,
    PromotionEvaluation,
    PromotionWorkflowState,
    apply_promotion,
    evaluate_promotion,
    load_capability_registry,
    load_promotion_policy,
    load_promotion_workflow,
    registry_metrics,
)
from cepio.domain_onboarding import load_domain_manifest, run_domain_onboarding
from cepio.generalization import load_pack, run_harness
from cepio.runtime_coverage import run_runtime_coverage


class RegressionTarget(BaseModel):
    id: str
    domain: str
    archetype: str
    competency: str
    personas: str
    standards: str
    runtime_suite: str | None = None
    minimum_semantic_pass_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    minimum_runtime_coverage_rate: float = Field(default=1.0, ge=0.0, le=1.0)


class RegressionSuite(BaseModel):
    id: str
    version: str
    targets: list[RegressionTarget] = Field(min_length=1)


class PromotionPack(BaseModel):
    id: str
    version: str
    candidates: list[PromotionCandidate] = Field(default_factory=list)


class HumanDecisionPack(BaseModel):
    id: str
    version: str
    decisions: list[HumanDecision] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_subjects(self) -> "HumanDecisionPack":
        subjects = [item.subject_id for item in self.decisions]
        if len(subjects) != len(set(subjects)):
            raise ValueError("human decision pack contains duplicate promotion subjects")
        return self


class ReleaseDecision(BaseModel):
    id: str
    domain: str
    decision: PromotionDecisionValue
    actor_role: str
    rationale: str

    @model_validator(mode="after")
    def human_only(self) -> "ReleaseDecision":
        lowered = self.actor_role.lower()
        if "agent" in lowered or lowered.startswith("ai") or " ai" in lowered:
            raise ValueError("AI/agent roles cannot approve domain release")
        return self


class PromotionDraft(BaseModel):
    id: str
    question_id: str
    proposed_layer: str
    missing_semantics: list[str]
    rationale: str
    proposed_resolution: str


class PromotionRunResult(BaseModel):
    candidate_id: str
    state: PromotionWorkflowState
    evaluation: PromotionEvaluation
    source_gap_ids: set[str] = Field(default_factory=set)


def _load_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return raw


def _load_json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return raw


def _repo_artifact(repo_root: Path, value: str) -> Path:
    if Path(value).is_absolute():
        raise ValueError(
            f"compounding artifact path must be repository-relative: {value}"
        )
    root = repo_root.resolve()
    candidate = (root / value).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"compounding artifact escapes repository root: {value}")
    if not candidate.is_file():
        raise FileNotFoundError(
            f"required compounding artifact not found: {value}"
        )
    return candidate


def _resolve(root: Path, value: Path | None) -> Path | None:
    if value is None:
        return None
    return value if value.is_absolute() else root / value


def load_regression_suite(path: Path) -> RegressionSuite:
    return RegressionSuite.model_validate(_load_yaml(path))


def load_promotion_pack(path: Path) -> PromotionPack:
    return PromotionPack.model_validate(_load_yaml(path))


def load_human_decisions(path: Path) -> HumanDecisionPack:
    return HumanDecisionPack.model_validate(_load_yaml(path))


def discover_promotion_drafts(
    repo_root: Path, domain_manifest_path: Path
) -> list[PromotionDraft]:
    manifest = load_domain_manifest(domain_manifest_path)
    if not manifest.artifacts.gap_triage:
        return []
    triage = _load_yaml(
        _repo_artifact(repo_root, manifest.artifacts.gap_triage)
    )
    result: list[PromotionDraft] = []
    for decision in triage.get("decisions", []) or []:
        if not isinstance(decision, dict):
            continue
        if decision.get("disposition") not in {"CORE", "COMMON"}:
            continue
        result.append(
            PromotionDraft(
                id=str(decision.get("id")),
                question_id=str(decision.get("question_id")),
                proposed_layer=str(decision.get("disposition")),
                missing_semantics=[
                    str(item)
                    for item in decision.get("missing_semantics", [])
                ],
                rationale=str(decision.get("rationale", "")),
                proposed_resolution=str(
                    decision.get("proposed_resolution", "")
                ),
            )
        )
    return result


def run_cross_domain_regression(
    repo_root: Path, suite_path: Path
) -> dict[str, Any]:
    suite = load_regression_suite(suite_path)
    results: list[dict[str, Any]] = []
    for target in suite.targets:
        semantic = run_harness(
            repo_root,
            _repo_artifact(repo_root, target.archetype),
            _repo_artifact(repo_root, target.competency),
            _repo_artifact(repo_root, target.personas),
            _repo_artifact(repo_root, target.standards),
            None,
        )
        semantic_rate = float(semantic["semantic_check_pass_rate"])
        semantic_ok = (
            semantic_rate >= target.minimum_semantic_pass_rate
            and semantic["status_counts"].get("FAIL", 0) == 0
            and semantic["status_counts"].get("ERROR", 0) == 0
        )
        runtime: dict[str, Any] | None = None
        runtime_ok = True
        if target.runtime_suite:
            runtime = run_runtime_coverage(
                repo_root,
                _repo_artifact(repo_root, target.runtime_suite),
            )
            runtime_rate = float(runtime["runtime_coverage_rate"])
            runtime_ok = (
                runtime_rate >= target.minimum_runtime_coverage_rate
                and runtime["status_counts"].get("FAIL", 0) == 0
                and runtime["status_counts"].get("ERROR", 0) == 0
            )
        results.append(
            {
                "id": target.id,
                "domain": target.domain,
                "status": "PASS" if semantic_ok and runtime_ok else "FAIL",
                "semantic_pass_rate": semantic_rate,
                "runtime_coverage_rate": (
                    runtime["runtime_coverage_rate"]
                    if runtime is not None
                    else None
                ),
                "semantic": semantic,
                "runtime": runtime,
            }
        )
    passed = sum(item["status"] == "PASS" for item in results)
    return {
        "suite_id": suite.id,
        "suite_version": suite.version,
        "target_count": len(results),
        "passed_targets": passed,
        "failed_targets": len(results) - passed,
        "survival_rate": passed / len(results),
        "results": results,
    }


def _semantic_contract_reuse(
    registry: CapabilityRegistry, competency_path: Path
) -> tuple[float, int, int]:
    pack = load_pack(competency_path)
    required: set[str] = set()
    for question in pack.questions:
        required.update(item.iri for item in question.terms)
        required.update(item.predicate for item in question.edges)
        for capability in question.capabilities:
            for pattern in capability.alternatives:
                required.update(item.iri for item in pattern.terms)
                required.update(item.predicate for item in pattern.edges)
    known: set[str] = set()
    for capability in registry.capabilities:
        known.update(capability.semantic_terms)
        known.update(capability.semantic_relationships)
    reused = len(required.intersection(known))
    return (
        reused / len(required) if required else 0.0,
        reused,
        len(required),
    )


def compounding_metrics(
    registry: CapabilityRegistry,
    *,
    onboarding_report: dict[str, Any],
    domain_competency_path: Path,
    regression_survival_rate: float,
    promotion_candidates: int,
    promotions_applied: int,
) -> dict[str, Any]:
    metrics = registry_metrics(registry)
    reuse_rate, reused_contracts, required_contracts = _semantic_contract_reuse(
        registry, domain_competency_path
    )
    baseline = onboarding_report.get("semantic_baseline") or {}
    domain_question_ids = {
        item["id"] for item in baseline.get("results", [])
    }
    reusable_question_ids = {
        competency.split(":", 1)[-1]
        for capability in registry.capabilities
        if capability.layer.value in {"CORE", "COMMON"}
        for competency in capability.competencies
    }
    covered_questions = len(
        domain_question_ids.intersection(reusable_question_ids)
    )
    domain_delta = onboarding_report.get("domain_delta") or {}
    question_count = int(
        domain_delta.get("question_count", len(domain_question_ids))
    )
    semantic_gap_count = int(domain_delta.get("semantic_gap_count", 0))
    metrics.update(
        {
            "semantic_contract_reuse_rate": reuse_rate,
            "reused_semantic_contracts": reused_contracts,
            "required_semantic_contracts": required_contracts,
            "reusable_competency_coverage_rate": (
                covered_questions / len(domain_question_ids)
                if domain_question_ids
                else 0.0
            ),
            "new_semantic_gap_count": semantic_gap_count,
            "marginal_gap_rate": (
                semantic_gap_count / question_count
                if question_count
                else 0.0
            ),
            "regression_survival_rate": regression_survival_rate,
            "promotion_candidate_count": promotion_candidates,
            "promotions_applied": promotions_applied,
            "cross_domain_promotion_rate": (
                promotions_applied / promotion_candidates
                if promotion_candidates
                else 0.0
            ),
        }
    )
    return metrics


def _promotion_state(
    evaluation: PromotionEvaluation,
) -> PromotionWorkflowState:
    if evaluation.status == "APPROVED":
        return PromotionWorkflowState.PROMOTED
    if evaluation.status == "REJECTED":
        return PromotionWorkflowState.REJECTED
    if evaluation.status == "READY_FOR_HUMAN_REVIEW":
        return PromotionWorkflowState.ARCHITECTURE_REVIEW
    return PromotionWorkflowState.BLOCKED


def _validate_promotion_workflow(path: Path) -> str:
    contract = load_promotion_workflow(path)
    required = {
        (
            PromotionWorkflowState.CANDIDATE,
            PromotionWorkflowState.EVIDENCE_COLLECTED,
        ),
        (
            PromotionWorkflowState.EVIDENCE_COLLECTED,
            PromotionWorkflowState.CROSS_DOMAIN_TESTED,
        ),
        (
            PromotionWorkflowState.CROSS_DOMAIN_TESTED,
            PromotionWorkflowState.ARCHITECTURE_REVIEW,
        ),
        (
            PromotionWorkflowState.ARCHITECTURE_REVIEW,
            PromotionWorkflowState.APPROVED,
        ),
        (
            PromotionWorkflowState.APPROVED,
            PromotionWorkflowState.PROMOTED,
        ),
    }
    declared = {(item.source, item.target) for item in contract.transitions}
    missing = sorted(
        f"{source.value}->{target.value}"
        for source, target in required - declared
    )
    if missing:
        raise ValueError(
            f"promotion workflow is missing required transitions: {missing}"
        )
    return contract.id


def _release_gate(
    *,
    domain: str,
    onboarding_status: str,
    regression_survival_rate: float,
    unresolved_drafts: int,
    promotion_blockers: list[str],
    release_decision: ReleaseDecision | None,
) -> tuple[bool, list[str], bool]:
    blockers = list(promotion_blockers)
    if onboarding_status != "READY_FOR_HUMAN_REVIEW":
        blockers.append(
            "domain onboarding has not reached Generalization Review"
        )
    if regression_survival_rate < 1.0:
        blockers.append("cross-domain regression must survive at 100%")
    if unresolved_drafts:
        blockers.append(
            f"{unresolved_drafts} Generalization Review promotion drafts "
            "remain unresolved"
        )
    if blockers:
        return False, blockers, False
    if release_decision is None:
        return False, [], True
    if release_decision.domain != domain:
        return False, [
            "release approval domain does not match onboarding domain"
        ], False
    if release_decision.decision != PromotionDecisionValue.APPROVE:
        return False, ["domain release was not approved"], False
    return True, [], False


def run_cycle(
    repo_root: Path,
    *,
    domain_manifest_path: Path,
    domain_workflow_path: Path,
    domain_policy_path: Path,
    registry_path: Path,
    regression_suite_path: Path,
    promotion_policy_path: Path,
    promotion_workflow_path: Path,
    onboarding_report_path: Path | None = None,
    promotion_pack_path: Path | None = None,
    promotion_decisions_path: Path | None = None,
    release_decision_path: Path | None = None,
) -> dict[str, Any]:
    onboarding = (
        _load_json(onboarding_report_path)
        if onboarding_report_path is not None
        else run_domain_onboarding(
            repo_root,
            domain_manifest_path,
            domain_workflow_path,
            domain_policy_path,
        )
    )
    registry = load_capability_registry(registry_path)
    before = registry_metrics(registry)
    if onboarding["status"] == "BLOCKED":
        return {
            "status": "BLOCKED",
            "state": "DOMAIN_ONBOARDING",
            "domain": onboarding["domain"],
            "onboarding": onboarding,
            "registry_metrics_before": before,
            "registry_metrics_after": before,
            "next_action": (
                "Resolve Domain Onboarding blockers before generalization."
            ),
        }

    promotion_workflow_id = _validate_promotion_workflow(
        promotion_workflow_path
    )
    regression = run_cross_domain_regression(
        repo_root, regression_suite_path
    )
    drafts = discover_promotion_drafts(repo_root, domain_manifest_path)
    promotion_policy = load_promotion_policy(promotion_policy_path)
    candidates = (
        load_promotion_pack(promotion_pack_path).candidates
        if promotion_pack_path is not None
        else []
    )
    decisions = (
        {
            item.subject_id: item
            for item in load_human_decisions(
                promotion_decisions_path
            ).decisions
        }
        if promotion_decisions_path is not None
        else {}
    )

    updated = registry
    promotion_runs: list[PromotionRunResult] = []
    hard_promotion_blockers: list[str] = []
    resolved_gap_ids: set[str] = set()
    promotions_applied = 0
    for candidate in candidates:
        evaluation = evaluate_promotion(
            candidate,
            decision=decisions.get(candidate.id),
            regression_survival_rate=float(regression["survival_rate"]),
            policy=promotion_policy,
        )
        state = _promotion_state(evaluation)
        promotion_runs.append(
            PromotionRunResult(
                candidate_id=candidate.id,
                state=state,
                evaluation=evaluation,
                source_gap_ids=candidate.source_gap_ids,
            )
        )
        if evaluation.status == "APPROVED":
            updated = apply_promotion(updated, candidate, evaluation)
            resolved_gap_ids.update(candidate.source_gap_ids)
            promotions_applied += 1
        elif evaluation.status == "REJECTED":
            resolved_gap_ids.update(candidate.source_gap_ids)
        elif evaluation.status == "BLOCKED":
            hard_promotion_blockers.extend(
                f"{candidate.id}: {blocker}"
                for blocker in evaluation.blockers
            )

    unresolved_drafts = {item.id for item in drafts} - resolved_gap_ids
    release_decision = (
        ReleaseDecision.model_validate(_load_yaml(release_decision_path))
        if release_decision_path is not None
        else None
    )
    released, release_blockers, awaiting_release_approval = _release_gate(
        domain=onboarding["domain"],
        onboarding_status=onboarding["status"],
        regression_survival_rate=float(regression["survival_rate"]),
        unresolved_drafts=len(unresolved_drafts),
        promotion_blockers=hard_promotion_blockers,
        release_decision=release_decision,
    )
    manifest = load_domain_manifest(domain_manifest_path)
    competency_path = _repo_artifact(
        repo_root, manifest.artifacts.competency
    )
    after = compounding_metrics(
        updated,
        onboarding_report=onboarding,
        domain_competency_path=competency_path,
        regression_survival_rate=float(regression["survival_rate"]),
        promotion_candidates=len(candidates),
        promotions_applied=promotions_applied,
    )

    if released:
        status = "RELEASED"
        state = "DOMAIN_RELEASED"
        next_action = (
            "Persist the reviewed registry update as a new version and publish "
            "release evidence."
        )
    elif release_blockers:
        status = "BLOCKED"
        state = "GENERALIZATION_REVIEW"
        next_action = (
            "Resolve promotion/regression blockers and rerun the frozen evidence set."
        )
    elif unresolved_drafts or any(
        item.state == PromotionWorkflowState.ARCHITECTURE_REVIEW
        for item in promotion_runs
    ):
        status = "READY_FOR_GENERALIZATION_REVIEW"
        state = "GENERALIZATION_REVIEW"
        next_action = (
            "Approve or reject promotion candidates; automation cannot "
            "self-promote capability."
        )
    elif awaiting_release_approval:
        status = "READY_FOR_RELEASE_REVIEW"
        state = "RELEASE_REVIEW"
        next_action = (
            "A human release authority may approve or reject the domain release."
        )
    else:
        status = "BLOCKED"
        state = "RELEASE_REVIEW"
        next_action = "Resolve the release decision before publication."

    return {
        "status": status,
        "state": state,
        "domain": onboarding["domain"],
        "onboarding": onboarding,
        "promotion_workflow_id": promotion_workflow_id,
        "promotion_drafts": [
            item.model_dump(mode="json") for item in drafts
        ],
        "unresolved_promotion_draft_ids": sorted(unresolved_drafts),
        "promotion_runs": [
            item.model_dump(mode="json") for item in promotion_runs
        ],
        "regression": regression,
        "registry_metrics_before": before,
        "registry_metrics_after": after,
        "updated_registry": updated.model_dump(mode="json"),
        "promotions_applied": promotions_applied,
        "release_blockers": release_blockers,
        "human_release_approval_required": awaiting_release_approval,
        "next_action": next_action,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the CEPIO compounding industrial-intelligence control loop"
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument(
        "--domain-manifest",
        type=Path,
        default=Path(
            "generalization/domain-packs/refinery-reference-v0.1.yaml"
        ),
    )
    parser.add_argument(
        "--domain-workflow",
        type=Path,
        default=Path("workflows/domain-onboarding-v0.1.yaml"),
    )
    parser.add_argument(
        "--domain-policy",
        type=Path,
        default=Path("policies/domain-onboarding-v0.1.yaml"),
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path(
            "generalization/capabilities/registry-v0.1.yaml"
        ),
    )
    parser.add_argument(
        "--regression-suite",
        type=Path,
        default=Path(
            "generalization/regression/industrial-common-v0.1.yaml"
        ),
    )
    parser.add_argument(
        "--promotion-policy",
        type=Path,
        default=Path("policies/capability-promotion-v0.1.yaml"),
    )
    parser.add_argument(
        "--promotion-workflow",
        type=Path,
        default=Path("workflows/capability-promotion-v0.1.yaml"),
    )
    parser.add_argument("--onboarding-report", type=Path)
    parser.add_argument("--promotion-pack", type=Path)
    parser.add_argument("--promotion-decisions", type=Path)
    parser.add_argument("--release-decision", type=Path)
    parser.add_argument("--registry-out", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--fail-on-blocked", action="store_true")
    args = parser.parse_args()

    root = args.repo_root.resolve()
    report = run_cycle(
        root,
        domain_manifest_path=_resolve(root, args.domain_manifest),
        domain_workflow_path=_resolve(root, args.domain_workflow),
        domain_policy_path=_resolve(root, args.domain_policy),
        registry_path=_resolve(root, args.registry),
        regression_suite_path=_resolve(root, args.regression_suite),
        promotion_policy_path=_resolve(root, args.promotion_policy),
        promotion_workflow_path=_resolve(root, args.promotion_workflow),
        onboarding_report_path=_resolve(root, args.onboarding_report),
        promotion_pack_path=_resolve(root, args.promotion_pack),
        promotion_decisions_path=_resolve(root, args.promotion_decisions),
        release_decision_path=_resolve(root, args.release_decision),
    )
    print("CEPIO Compounding Industrial Intelligence v0.1")
    print(f"domain: {report['domain']}")
    print(f"state: {report['state']}")
    print(f"status: {report['status']}")
    regression = report.get("regression")
    if regression:
        print(
            f"regression survival: {regression['survival_rate']:.1%}"
        )
    metrics = report.get("registry_metrics_after") or {}
    if "semantic_contract_reuse_rate" in metrics:
        print(
            "semantic contract reuse: "
            f"{metrics['semantic_contract_reuse_rate']:.1%}"
        )
        print(
            "reusable competency coverage: "
            f"{metrics['reusable_competency_coverage_rate']:.1%}"
        )
        print(
            f"marginal gap rate: {metrics['marginal_gap_rate']:.1%}"
        )
    print(
        f"next: {report.get('next_action', 'Review generated evidence.')}"
    )

    registry_out = _resolve(root, args.registry_out)
    if registry_out is not None and report.get("updated_registry") is not None:
        registry_out.parent.mkdir(parents=True, exist_ok=True)
        registry_out.write_text(
            yaml.safe_dump(
                report["updated_registry"], sort_keys=False
            ),
            encoding="utf-8",
        )
    json_out = _resolve(root, args.json_out)
    if json_out is not None:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return (
        2
        if args.fail_on_blocked and report["status"] == "BLOCKED"
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())

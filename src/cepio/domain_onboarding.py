"""Governed control-plane workflow for CEPIO domain onboarding.

The workflow turns the Generalization Lab pattern into a deterministic, auditable
state machine over repository artifacts. It deliberately stops at the human
Generalization Review gate in v0.1; release approval is never inferred from CI.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from .generalization import (
    load_archetype,
    load_pack,
    load_personas,
    load_standards,
    run_harness,
)
from .runtime_coverage import run_runtime_coverage


class DomainOnboardingState(str, Enum):
    REQUESTED = "REQUESTED"
    SCOPED = "SCOPED"
    BENCHMARKED = "BENCHMARKED"
    BASELINED = "BASELINED"
    GAP_ANALYZED = "GAP_ANALYZED"
    QUALIFYING = "QUALIFYING"
    QUALIFIED = "QUALIFIED"
    GENERALIZATION_REVIEW = "GENERALIZATION_REVIEW"
    RELEASE_CANDIDATE = "RELEASE_CANDIDATE"
    RELEASED = "RELEASED"
    BLOCKED = "BLOCKED"
    REJECTED = "REJECTED"
    DEPRECATED = "DEPRECATED"


class WorkflowTransition(BaseModel):
    source: DomainOnboardingState
    target: DomainOnboardingState
    gate: str


class DomainWorkflowContract(BaseModel):
    id: str
    version: str
    initial_state: DomainOnboardingState
    states: list[DomainOnboardingState]
    transitions: list[WorkflowTransition]


class DomainArtifacts(BaseModel):
    archetype: str
    personas: str
    standards: str
    competency: str
    gap_triage: str | None = None
    runtime_suite: str | None = None


class DomainOnboardingManifest(BaseModel):
    id: str
    version: str
    domain: str
    name: str
    mode: str = "new-domain"
    adjacent_domains: list[str] = Field(default_factory=list)
    artifacts: DomainArtifacts


class QualificationPolicy(BaseModel):
    minimum_semantic_pass_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    maximum_critical_failures: int = Field(default=0, ge=0)
    require_runtime: bool = True
    minimum_runtime_coverage_rate: float = Field(default=1.0, ge=0.0, le=1.0)


class DomainOnboardingPolicy(BaseModel):
    id: str
    version: str
    require_frozen_benchmark: bool = True
    allowed_gap_dispositions: list[str]
    human_review_states: list[DomainOnboardingState] = Field(default_factory=list)
    qualification: QualificationPolicy = Field(default_factory=QualificationPolicy)


def _load_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return raw


def load_domain_manifest(path: Path) -> DomainOnboardingManifest:
    return DomainOnboardingManifest.model_validate(_load_yaml(path))


def load_domain_workflow(path: Path) -> DomainWorkflowContract:
    contract = DomainWorkflowContract.model_validate(_load_yaml(path))
    states = set(contract.states)
    if contract.initial_state not in states:
        raise ValueError("workflow initial_state must be declared in states")
    for transition in contract.transitions:
        if transition.source not in states or transition.target not in states:
            raise ValueError(
                f"workflow transition {transition.source.value}->{transition.target.value} "
                "references an undeclared state"
            )
    return contract


def load_domain_policy(path: Path) -> DomainOnboardingPolicy:
    policy = DomainOnboardingPolicy.model_validate(_load_yaml(path))
    if len(policy.allowed_gap_dispositions) != len(set(policy.allowed_gap_dispositions)):
        raise ValueError("allowed_gap_dispositions must be unique")
    return policy


def _artifact_path(repo_root: Path, value: str) -> Path:
    if Path(value).is_absolute():
        raise ValueError(f"domain artifact path must be repository-relative: {value}")
    root = repo_root.resolve()
    candidate = (root / value).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError(f"domain artifact escapes repository root: {value}")
    if not candidate.is_file():
        raise FileNotFoundError(f"required domain artifact not found: {value}")
    return candidate


def _can_transition(
    contract: DomainWorkflowContract,
    source: DomainOnboardingState,
    target: DomainOnboardingState,
) -> bool:
    return any(item.source == source and item.target == target for item in contract.transitions)


def _expected_gap_keys(baseline: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        (result["id"], missing)
        for result in baseline["results"]
        if result["status"] in {"PARTIAL", "FAIL"}
        for missing in result["missing"]
    }


def _validate_gap_triage(
    path: Path,
    *,
    expected: set[tuple[str, str]],
    archetype_id: str,
    competency_pack_id: str,
    question_ids: set[str],
    standard_ids: set[str],
    allowed_dispositions: set[str],
) -> dict[str, Any]:
    triage = _load_yaml(path)
    if triage.get("status") != "accepted":
        raise ValueError("gap triage must be accepted")
    if triage.get("archetype_id") != archetype_id:
        raise ValueError("gap triage archetype_id does not match domain archetype")
    if triage.get("competency_pack_id") != competency_pack_id:
        raise ValueError("gap triage competency_pack_id does not match frozen benchmark")

    decisions = triage.get("decisions", [])
    if not isinstance(decisions, list):
        raise ValueError("gap triage decisions must be a list")

    covered: set[tuple[str, str]] = set()
    duplicates: set[tuple[str, str]] = set()
    counts = {item: 0 for item in sorted(allowed_dispositions)}
    unknown_questions: set[str] = set()
    unknown_standards: set[str] = set()

    for decision in decisions:
        if not isinstance(decision, dict):
            raise ValueError("each gap decision must be a mapping")
        question_id = str(decision.get("question_id", ""))
        disposition = str(decision.get("disposition", ""))
        if question_id not in question_ids:
            unknown_questions.add(question_id)
        if disposition not in allowed_dispositions:
            raise ValueError(f"unsupported gap disposition: {disposition}")
        counts[disposition] += 1
        for standard_id in decision.get("standards", []) or []:
            if standard_id not in standard_ids:
                unknown_standards.add(str(standard_id))
        missing_semantics = decision.get("missing_semantics", [])
        if not isinstance(missing_semantics, list) or not missing_semantics:
            raise ValueError(f"gap decision {decision.get('id')} must cover missing_semantics")
        for missing in missing_semantics:
            key = (question_id, str(missing))
            if key in covered:
                duplicates.add(key)
            covered.add(key)

    if unknown_questions:
        raise ValueError(f"gap triage references unknown question ids: {sorted(unknown_questions)}")
    if unknown_standards:
        raise ValueError(
            f"gap triage references unknown standards ids: {sorted(unknown_standards)}"
        )
    if duplicates:
        raise ValueError(f"gap triage contains duplicate coverage: {sorted(duplicates)}")

    untriaged = sorted(expected - covered)
    stale = sorted(covered - expected)
    if untriaged:
        raise ValueError(f"current semantic gaps are not triaged: {untriaged}")
    if stale:
        raise ValueError(f"gap triage contains stale/non-current gaps: {stale}")

    return {
        "decision_count": len(decisions),
        "disposition_counts": counts,
        "triage_id": triage.get("id"),
        "triage_version": triage.get("version"),
    }


def run_domain_onboarding(
    repo_root: Path,
    manifest_path: Path,
    workflow_path: Path,
    policy_path: Path,
) -> dict[str, Any]:
    """Run the deterministic v0.1 domain-onboarding workflow.

    Successful automation terminates at GENERALIZATION_REVIEW. Human promotion and
    release approvals are explicit follow-on gates and are not synthesized by CI.
    """

    repo_root = repo_root.resolve()
    manifest = load_domain_manifest(manifest_path)
    contract = load_domain_workflow(workflow_path)
    policy = load_domain_policy(policy_path)

    state = contract.initial_state
    timeline: list[dict[str, Any]] = []
    baseline: dict[str, Any] | None = None
    runtime_report: dict[str, Any] | None = None
    gap_summary: dict[str, Any] = {
        "decision_count": 0,
        "disposition_counts": {item: 0 for item in sorted(set(policy.allowed_gap_dispositions))},
        "triage_id": None,
        "triage_version": None,
    }

    def transition(
        target: DomainOnboardingState,
        gate: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        nonlocal state
        if not _can_transition(contract, state, target):
            raise ValueError(f"workflow forbids transition {state.value}->{target.value}")
        timeline.append(
            {
                "from": state.value,
                "to": target.value,
                "gate": gate,
                "details": details or {},
            }
        )
        state = target

    def blocked(gate: str, reason: str) -> dict[str, Any]:
        if state != DomainOnboardingState.BLOCKED:
            transition(DomainOnboardingState.BLOCKED, gate, {"reason": reason})
        return {
            "workflow_id": contract.id,
            "workflow_version": contract.version,
            "policy_id": policy.id,
            "manifest_id": manifest.id,
            "domain": manifest.domain,
            "current_state": state.value,
            "status": "BLOCKED",
            "block_reason": reason,
            "timeline": timeline,
            "semantic_baseline": baseline,
            "gap_analysis": gap_summary,
            "runtime_qualification": runtime_report,
            "next_action": "Resolve the failing policy gate and rerun the same frozen workflow inputs.",
        }

    # Scope gate: all declared evidence must exist inside the repository.
    try:
        archetype_path = _artifact_path(repo_root, manifest.artifacts.archetype)
        personas_path = _artifact_path(repo_root, manifest.artifacts.personas)
        standards_path = _artifact_path(repo_root, manifest.artifacts.standards)
        competency_path = _artifact_path(repo_root, manifest.artifacts.competency)
        gap_path = (
            _artifact_path(repo_root, manifest.artifacts.gap_triage)
            if manifest.artifacts.gap_triage
            else None
        )
        runtime_path = (
            _artifact_path(repo_root, manifest.artifacts.runtime_suite)
            if manifest.artifacts.runtime_suite
            else None
        )
        archetype = load_archetype(archetype_path)
        personas = load_personas(personas_path)
        standards = load_standards(standards_path)
        pack = load_pack(competency_path)
    except Exception as exc:
        return blocked("scope_complete", str(exc))

    if pack.archetype_id != archetype.id:
        return blocked(
            "scope_complete",
            f"competency archetype {pack.archetype_id!r} != scoped archetype {archetype.id!r}",
        )
    if not personas.personas:
        return blocked("scope_complete", "persona pack must contain at least one persona")
    if not standards.references:
        return blocked("scope_complete", "standards registry must contain at least one reference")

    transition(
        DomainOnboardingState.SCOPED,
        "scope_complete",
        {
            "archetype_id": archetype.id,
            "persona_count": len(personas.personas),
            "standard_count": len(standards.references),
            "adjacent_domains": manifest.adjacent_domains,
        },
    )

    if policy.require_frozen_benchmark and not pack.frozen:
        return blocked("benchmark_frozen", "competency benchmark must be frozen before baseline")
    transition(
        DomainOnboardingState.BENCHMARKED,
        "benchmark_frozen",
        {
            "competency_pack_id": pack.id,
            "question_count": len(pack.questions),
            "frozen": pack.frozen,
        },
    )

    try:
        baseline = run_harness(
            repo_root,
            archetype_path,
            competency_path,
            personas_path,
            standards_path,
            None,
        )
    except Exception as exc:
        return blocked("baseline_executable", str(exc))

    transition(
        DomainOnboardingState.BASELINED,
        "baseline_executable",
        {
            "batch_hash": baseline["batch_hash"],
            "ontology_hash": baseline["ontology_hash"],
            "semantic_pass_rate": baseline["semantic_check_pass_rate"],
            "status_counts": baseline["status_counts"],
        },
    )

    expected_gaps = _expected_gap_keys(baseline)
    if expected_gaps:
        if gap_path is None:
            return blocked(
                "gap_classification_complete",
                f"{len(expected_gaps)} current semantic gaps require an accepted triage pack",
            )
        try:
            gap_summary = _validate_gap_triage(
                gap_path,
                expected=expected_gaps,
                archetype_id=archetype.id,
                competency_pack_id=pack.id,
                question_ids={question.id for question in pack.questions},
                standard_ids={item.id for item in standards.references},
                allowed_dispositions=set(policy.allowed_gap_dispositions),
            )
        except Exception as exc:
            return blocked("gap_classification_complete", str(exc))

    transition(
        DomainOnboardingState.GAP_ANALYZED,
        "gap_classification_complete",
        {
            "semantic_gap_count": len(expected_gaps),
            **gap_summary,
        },
    )

    transition(DomainOnboardingState.QUALIFYING, "qualification_started")

    qualification_failures: list[str] = []
    semantic_rate = float(baseline["semantic_check_pass_rate"])
    critical_failures = [
        result["id"]
        for result in baseline["results"]
        if result["priority"] == "critical" and result["status"] != "PASS"
    ]
    if semantic_rate < policy.qualification.minimum_semantic_pass_rate:
        qualification_failures.append(
            "semantic pass rate "
            f"{semantic_rate:.3f} < {policy.qualification.minimum_semantic_pass_rate:.3f}"
        )
    if len(critical_failures) > policy.qualification.maximum_critical_failures:
        qualification_failures.append(
            f"critical failures {critical_failures} exceed maximum "
            f"{policy.qualification.maximum_critical_failures}"
        )
    if baseline["status_counts"].get("ERROR", 0):
        qualification_failures.append("semantic baseline contains ERROR results")

    if runtime_path is not None:
        try:
            runtime_report = run_runtime_coverage(repo_root, runtime_path)
        except Exception as exc:
            return blocked("runtime_qualification", str(exc))
        runtime_rate = float(runtime_report["runtime_coverage_rate"])
        if runtime_rate < policy.qualification.minimum_runtime_coverage_rate:
            qualification_failures.append(
                "runtime coverage rate "
                f"{runtime_rate:.3f} < {policy.qualification.minimum_runtime_coverage_rate:.3f}"
            )
        if runtime_report["status_counts"].get("FAIL", 0) or runtime_report["status_counts"].get(
            "ERROR", 0
        ):
            qualification_failures.append("runtime qualification contains FAIL/ERROR results")
    elif policy.qualification.require_runtime:
        qualification_failures.append("policy requires a runtime qualification suite")

    if qualification_failures:
        return blocked("qualification_policy", "; ".join(qualification_failures))

    transition(
        DomainOnboardingState.QUALIFIED,
        "qualification_policy",
        {
            "semantic_pass_rate": semantic_rate,
            "critical_failures": critical_failures,
            "runtime_coverage_rate": (
                runtime_report["runtime_coverage_rate"] if runtime_report is not None else None
            ),
        },
    )

    transition(
        DomainOnboardingState.GENERALIZATION_REVIEW,
        "human_generalization_review",
        {
            "human_review_required": True,
            "allowed_gap_dispositions": policy.allowed_gap_dispositions,
        },
    )

    return {
        "workflow_id": contract.id,
        "workflow_version": contract.version,
        "policy_id": policy.id,
        "manifest_id": manifest.id,
        "domain": manifest.domain,
        "mode": manifest.mode,
        "current_state": state.value,
        "status": "READY_FOR_HUMAN_REVIEW",
        "timeline": timeline,
        "domain_delta": {
            "question_count": baseline["question_count"],
            "semantic_status_counts": baseline["status_counts"],
            "semantic_pass_rate": semantic_rate,
            "semantic_gap_count": len(expected_gaps),
            "gap_decision_count": gap_summary["decision_count"],
            "gap_disposition_counts": gap_summary["disposition_counts"],
            "runtime_coverage_rate": (
                runtime_report["runtime_coverage_rate"] if runtime_report is not None else None
            ),
        },
        "semantic_baseline": baseline,
        "gap_analysis": gap_summary,
        "runtime_qualification": runtime_report,
        "human_review_required": state in policy.human_review_states,
        "next_action": (
            "Review cross-domain promotion candidates and approve or reject Generalization Review. "
            "v0.1 never promotes or releases a domain automatically."
        ),
    }

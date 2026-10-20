"""Persona-scoped qualification for CEPIO Industrial Capability Contracts (ICC).

This layer intentionally sits on top of the governed Domain Onboarding workflow.
The domain benchmark remains frozen and source-neutral; a persona binding selects the
subset of competency questions and runtime evidence that the persona actually consumes.
Customer-specific mappings, KPIs and execution authority remain binding-time concerns.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from .domain_onboarding import (
    _artifact_path,
    load_domain_manifest,
    load_domain_policy,
    run_domain_onboarding,
)
from .generalization import CompetencyQuestion, load_pack, load_personas


AUTHORITY_TAGS = {
    "authority",
    "accountability",
    "policy",
    "hse",
    "permit-to-work",
    "offshore-command",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return raw


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _scope_hash(persona_id: str, questions: list[CompetencyQuestion]) -> str:
    payload = {
        "persona_id": persona_id,
        "questions": [
            {
                "id": question.id,
                "capabilities": [capability.id for capability in question.capabilities],
            }
            for question in questions
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _semantic_scope(
    baseline: dict[str, Any], questions: list[CompetencyQuestion]
) -> dict[str, Any]:
    question_ids = {question.id for question in questions}
    scoped_results = [result for result in baseline["results"] if result["id"] in question_ids]
    result_by_id = {result["id"]: result for result in scoped_results}

    total_checks = sum(int(result["checks_total"]) for result in scoped_results)
    passed_checks = sum(int(result["checks_passed"]) for result in scoped_results)
    status_counts = {
        status: sum(result["status"] == status for result in scoped_results)
        for status in ("PASS", "PARTIAL", "FAIL", "ERROR")
    }

    required_capabilities: list[dict[str, Any]] = []
    reused_capabilities: list[dict[str, Any]] = []
    missing_capabilities: list[dict[str, Any]] = []
    semantic_gaps: list[dict[str, Any]] = []

    for question in questions:
        result = result_by_id.get(question.id)
        if result is None:
            semantic_gaps.append(
                {
                    "question_id": question.id,
                    "kind": "missing-qualification-result",
                    "missing": ["qualification-result"],
                }
            )
            continue

        details = {item["id"]: item for item in result.get("capability_details", [])}
        for capability in question.capabilities:
            record = {
                "question_id": question.id,
                "capability_id": capability.id,
                "description": capability.description,
            }
            required_capabilities.append(record)
            detail = details.get(capability.id)
            if detail and detail.get("ok"):
                reused_capabilities.append(
                    {
                        **record,
                        "matched_pattern": detail.get("matched_pattern"),
                    }
                )
            else:
                missing_capabilities.append(
                    {
                        **record,
                        "best_pattern": detail.get("best_pattern") if detail else None,
                    }
                )

        if result["status"] != "PASS":
            semantic_gaps.append(
                {
                    "question_id": question.id,
                    "status": result["status"],
                    "missing": list(result.get("missing", [])),
                }
            )

    critical_failures = [
        question.id
        for question in questions
        if question.priority == "critical"
        and result_by_id.get(question.id, {}).get("status") != "PASS"
    ]

    authority_question_ids = {
        question.id for question in questions if set(question.capability_tags) & AUTHORITY_TAGS
    }
    policy_authority_gaps = [
        gap for gap in semantic_gaps if gap["question_id"] in authority_question_ids
    ]

    return {
        "question_count": len(questions),
        "question_ids": [question.id for question in questions],
        "status_counts": status_counts,
        "semantic_pass_rate": (passed_checks / total_checks) if total_checks else 0.0,
        "critical_failures": critical_failures,
        "required_capabilities": required_capabilities,
        "reused_capabilities": reused_capabilities,
        "missing_capabilities": missing_capabilities,
        "semantic_gaps": semantic_gaps,
        "policy_authority_gaps": policy_authority_gaps,
        "results": scoped_results,
    }


def _runtime_scope(runtime_report: dict[str, Any] | None, question_ids: set[str]) -> dict[str, Any]:
    if runtime_report is None:
        return {
            "question_count": 0,
            "runtime_coverage_rate": 0.0,
            "status_counts": {"PASS": 0, "FAIL": 0, "ERROR": 0},
            "runtime_gaps": [
                {"question_id": question_id, "status": "MISSING_RUNTIME_REPORT"}
                for question_id in sorted(question_ids)
            ],
            "results": [],
        }

    results = [
        result for result in runtime_report.get("results", []) if result.get("question_id") in question_ids
    ]
    status_counts = {
        status: sum(result.get("status") == status for result in results)
        for status in ("PASS", "FAIL", "ERROR")
    }
    passed = status_counts["PASS"]
    runtime_gaps = [
        {
            "question_id": result.get("question_id"),
            "status": result.get("status"),
        }
        for result in results
        if result.get("status") != "PASS"
    ]
    missing = sorted(question_ids - {str(result.get("question_id")) for result in results})
    runtime_gaps.extend(
        {"question_id": question_id, "status": "MISSING_RUNTIME_CASE"}
        for question_id in missing
    )

    denominator = len(question_ids)
    return {
        "question_count": denominator,
        "runtime_coverage_rate": (passed / denominator) if denominator else 0.0,
        "status_counts": status_counts,
        "runtime_gaps": runtime_gaps,
        "results": results,
    }


def run_icc_persona_qualification(
    repo_root: Path,
    manifest_path: Path,
    workflow_path: Path,
    policy_path: Path,
    persona_id: str | None = None,
) -> dict[str, Any]:
    """Qualify one persona binding against a frozen domain ICC benchmark."""

    repo_root = repo_root.resolve()
    manifest_path = manifest_path.resolve()
    workflow_path = workflow_path.resolve()
    policy_path = policy_path.resolve()

    raw_manifest = _load_yaml(manifest_path)
    selected_persona_id = persona_id or raw_manifest.get("persona_id")
    manifest = load_domain_manifest(manifest_path)
    policy = load_domain_policy(policy_path)

    artifacts = manifest.artifacts
    competency_path = _artifact_path(repo_root, artifacts.competency)
    personas_path = _artifact_path(repo_root, artifacts.personas)
    archetype_path = _artifact_path(repo_root, artifacts.archetype)
    standards_path = _artifact_path(repo_root, artifacts.standards)
    runtime_path = (
        _artifact_path(repo_root, artifacts.runtime_suite) if artifacts.runtime_suite else None
    )

    pack = load_pack(competency_path)
    personas = load_personas(personas_path)

    base_provenance = {
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": _sha256_file(manifest_path),
        "workflow_sha256": _sha256_file(workflow_path),
        "policy_sha256": _sha256_file(policy_path),
        "archetype_sha256": _sha256_file(archetype_path),
        "persona_pack_sha256": _sha256_file(personas_path),
        "standards_sha256": _sha256_file(standards_path),
        "competency_pack_sha256": _sha256_file(competency_path),
        "runtime_suite_sha256": _sha256_file(runtime_path) if runtime_path else None,
    }

    if not selected_persona_id:
        return {
            "contract_type": "industrial-capability-contract-persona-binding",
            "contract_version": "0.1",
            "domain": manifest.domain,
            "status": "BLOCKED",
            "current_state": "BLOCKED",
            "block_reason": "persona qualification requires an explicit persona_id",
            "provenance": base_provenance,
        }

    persona = next((item for item in personas.personas if item.id == selected_persona_id), None)
    if persona is None:
        return {
            "contract_type": "industrial-capability-contract-persona-binding",
            "contract_version": "0.1",
            "contract_id": f"{manifest.id}:{selected_persona_id}",
            "domain": manifest.domain,
            "persona_id": selected_persona_id,
            "status": "BLOCKED",
            "current_state": "BLOCKED",
            "block_reason": f"persona {selected_persona_id!r} is not declared in the scoped persona pack",
            "provenance": base_provenance,
        }

    questions = [question for question in pack.questions if selected_persona_id in question.personas]
    if not questions:
        return {
            "contract_type": "industrial-capability-contract-persona-binding",
            "contract_version": "0.1",
            "contract_id": f"{manifest.id}:{selected_persona_id}",
            "domain": manifest.domain,
            "persona_id": selected_persona_id,
            "status": "BLOCKED",
            "current_state": "BLOCKED",
            "block_reason": f"persona {selected_persona_id!r} has no competency questions in frozen pack {pack.id!r}",
            "provenance": base_provenance,
        }

    domain_report = run_domain_onboarding(repo_root, manifest_path, workflow_path, policy_path)
    if domain_report["status"] == "BLOCKED":
        return {
            "contract_type": "industrial-capability-contract-persona-binding",
            "contract_version": "0.1",
            "contract_id": f"{manifest.id}:{selected_persona_id}",
            "domain": manifest.domain,
            "persona_id": selected_persona_id,
            "status": "BLOCKED",
            "current_state": "BLOCKED",
            "block_reason": f"parent domain onboarding blocked: {domain_report['block_reason']}",
            "domain_onboarding": domain_report,
            "provenance": base_provenance,
        }

    semantic = _semantic_scope(domain_report["semantic_baseline"], questions)
    runtime = _runtime_scope(
        domain_report.get("runtime_qualification"), set(semantic["question_ids"])
    )

    failures: list[str] = []
    if semantic["semantic_pass_rate"] < policy.qualification.minimum_semantic_pass_rate:
        failures.append(
            "persona semantic pass rate "
            f"{semantic['semantic_pass_rate']:.3f} < {policy.qualification.minimum_semantic_pass_rate:.3f}"
        )
    if len(semantic["critical_failures"]) > policy.qualification.maximum_critical_failures:
        failures.append(
            f"persona critical failures {semantic['critical_failures']} exceed maximum "
            f"{policy.qualification.maximum_critical_failures}"
        )
    if semantic["status_counts"]["ERROR"]:
        failures.append("persona semantic qualification contains ERROR results")
    if policy.qualification.require_runtime:
        if runtime["runtime_coverage_rate"] < policy.qualification.minimum_runtime_coverage_rate:
            failures.append(
                "persona runtime coverage rate "
                f"{runtime['runtime_coverage_rate']:.3f} < "
                f"{policy.qualification.minimum_runtime_coverage_rate:.3f}"
            )
        if runtime["runtime_gaps"]:
            failures.append("persona runtime qualification contains missing/failed evidence")

    qualification_status = "BLOCKED" if failures else "QUALIFIED"
    overall_status = "BLOCKED" if failures else "READY_FOR_HUMAN_REVIEW"
    current_state = "BLOCKED" if failures else domain_report["current_state"]

    customer_binding_requirements = [
        {"id": "source-mappings", "status": "REQUIRED_AT_CUSTOMER_ACTIVATION"},
        {"id": "customer-kpi-okr-bindings", "status": "REQUIRED_AT_CUSTOMER_ACTIVATION"},
        {"id": "local-policy-and-decision-rights", "status": "REQUIRED_AT_CUSTOMER_ACTIVATION"},
        {"id": "system-adapters-and-writeback", "status": "REQUIRED_AT_CUSTOMER_ACTIVATION"},
    ]

    provenance = {
        **base_provenance,
        "ontology_sha256": domain_report["semantic_baseline"].get("ontology_hash"),
        "semantic_batch_hash": domain_report["semantic_baseline"].get("batch_hash"),
        "runtime_suite_id": (
            domain_report.get("runtime_qualification") or {}
        ).get("suite_id"),
        "runtime_suite_hash": (
            domain_report.get("runtime_qualification") or {}
        ).get("suite_hash"),
        "persona_scope_hash": _scope_hash(selected_persona_id, questions),
    }

    return {
        "contract_type": "industrial-capability-contract-persona-binding",
        "contract_version": "0.1",
        "contract_id": f"{manifest.id}:{selected_persona_id}",
        "domain": manifest.domain,
        "persona_id": selected_persona_id,
        "qualification_status": qualification_status,
        "status": overall_status,
        "current_state": current_state,
        "block_reason": "; ".join(failures) if failures else None,
        "persona_binding": {
            "role": persona.role,
            "objectives": persona.objectives,
            "information_needs": persona.information_needs,
            "question_ids": semantic["question_ids"],
        },
        "qualification": {
            "semantic_pass_rate": semantic["semantic_pass_rate"],
            "semantic_status_counts": semantic["status_counts"],
            "critical_failures": semantic["critical_failures"],
            "runtime_coverage_rate": runtime["runtime_coverage_rate"],
            "runtime_status_counts": runtime["status_counts"],
        },
        "icc_delta": {
            "required_question_ids": semantic["question_ids"],
            "required_capabilities": semantic["required_capabilities"],
            "reused_capabilities": semantic["reused_capabilities"],
            "missing_capabilities": semantic["missing_capabilities"],
            "new_semantic_candidates": semantic["semantic_gaps"],
            "runtime_gaps": runtime["runtime_gaps"],
            "policy_authority_gaps": semantic["policy_authority_gaps"],
            "policy_authority_assessment_boundary": (
                "Semantic authority/accountability capability tags are qualified here; "
                "customer execution authority is evaluated at customer binding time."
            ),
            "customer_binding_requirements": customer_binding_requirements,
        },
        "semantic_qualification": semantic,
        "runtime_qualification": runtime,
        "domain_onboarding": {
            "manifest_id": domain_report["manifest_id"],
            "workflow_id": domain_report["workflow_id"],
            "workflow_version": domain_report["workflow_version"],
            "policy_id": domain_report["policy_id"],
            "current_state": domain_report["current_state"],
            "status": domain_report["status"],
        },
        "human_review_required": not failures,
        "provenance": provenance,
        "next_action": (
            "Review the persona ICC delta and customer-binding requirements in Generalization Review."
            if not failures
            else "Resolve the persona-scoped ICC qualification failures and rerun the same frozen inputs."
        ),
    }

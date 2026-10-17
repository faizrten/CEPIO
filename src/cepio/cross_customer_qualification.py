"""Deterministic cross-customer qualification for frozen CEPIO domain competencies.

Cross-customer qualification is intentionally stricter than a customer demo. A profile
may vary instance labels and synthetic operating context, but it may not modify the
canonical CEPIO graph contract. Every customer therefore executes the same frozen
competency pack, runtime question set, object/relationship types and probes.

This lets CEPIO distinguish genuine generalization from a collection of customer-specific
ontology forks. No LLM output participates in pass/fail.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .runtime_coverage import (
    RuntimeCoverageSuite,
    RuntimeObjectSpec,
    RuntimeProbe,
    RuntimeQuestionCase,
    RuntimeRelationshipSpec,
    load_runtime_coverage_suite,
    run_runtime_question,
)


class CustomerEvidenceSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    url: str


class CustomerQualificationProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    context: dict[str, str]
    scenario_theme: str
    source_evidence: list[CustomerEvidenceSource] = Field(default_factory=list)


class CrossCustomerQualificationPack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    version: str
    archetype_id: str
    competency_pack: str
    runtime_suite: str
    description: str = ""
    required_stress_dimensions: list[str]
    customers: list[CustomerQualificationProfile]


def _load_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return raw


def load_cross_customer_pack(path: Path) -> CrossCustomerQualificationPack:
    return CrossCustomerQualificationPack.model_validate(_load_yaml(path))


def _hash_payload(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _case_semantic_signature(case: RuntimeQuestionCase) -> dict[str, Any]:
    object_type_by_id = {obj.id: obj.type for obj in case.objects}
    return {
        "question_id": case.question_id,
        "capabilities": sorted(case.capabilities),
        "object_types": sorted(obj.type for obj in case.objects),
        "relationship_signatures": sorted(
            (
                rel.type,
                object_type_by_id[rel.source],
                object_type_by_id[rel.target],
            )
            for rel in case.relationships
        ),
        "probe_signatures": sorted(
            (
                probe.kind,
                probe.relationship_type or "",
                probe.direction,
                probe.property_name or "",
            )
            for probe in case.probes
        ),
    }


def suite_semantic_signature(suite: RuntimeCoverageSuite) -> dict[str, Any]:
    return {
        case.question_id: _case_semantic_signature(case)
        for case in suite.questions
    }


def _profile_case(case: RuntimeQuestionCase, profile: CustomerQualificationProfile) -> RuntimeQuestionCase:
    """Create an instance-only customer variant while preserving canonical semantics."""

    prefix = profile.id.upper().replace("-", "_")
    id_map = {obj.id: f"{prefix}:{obj.id}" for obj in case.objects}
    profile_properties = {
        "qualification:customer_profile": profile.id,
        "qualification:customer_name": profile.name,
        "qualification:scenario_theme": profile.scenario_theme,
        **{f"qualification:{key}": value for key, value in profile.context.items()},
        "qualification:synthetic_fixture": True,
    }

    objects = [
        RuntimeObjectSpec(
            id=id_map[obj.id],
            type=obj.type,
            name=f"{profile.name} | {obj.name}",
            properties={**obj.properties, **profile_properties},
            interfaces=obj.interfaces,
        )
        for obj in case.objects
    ]
    relationships = [
        RuntimeRelationshipSpec(
            id=f"{prefix}:{rel.id}",
            type=rel.type,
            source=id_map[rel.source],
            target=id_map[rel.target],
        )
        for rel in case.relationships
    ]

    probes: list[RuntimeProbe] = []
    for probe in case.probes:
        probes.append(
            RuntimeProbe(
                id=probe.id,
                kind=probe.kind,
                start_id=id_map.get(probe.start_id, probe.start_id) if probe.start_id else None,
                relationship_type=probe.relationship_type,
                direction=probe.direction,
                expected_ids=[id_map.get(object_id, object_id) for object_id in probe.expected_ids],
                object_id=id_map.get(probe.object_id, probe.object_id) if probe.object_id else None,
                property_name=probe.property_name,
                expected_value=probe.expected_value,
            )
        )

    return RuntimeQuestionCase(
        question_id=case.question_id,
        claim=case.claim,
        capabilities=list(case.capabilities),
        objects=objects,
        relationships=relationships,
        probes=probes,
    )


def _validate_pack(
    pack: CrossCustomerQualificationPack,
    suite: RuntimeCoverageSuite,
) -> dict[str, list[str]]:
    if pack.archetype_id != suite.archetype_id:
        raise ValueError(
            f"cross-customer archetype {pack.archetype_id!r} != runtime archetype {suite.archetype_id!r}"
        )
    if pack.competency_pack != suite.competency_pack:
        raise ValueError(
            "cross-customer qualification must target the exact competency pack used by the runtime suite"
        )
    if len(pack.customers) != len({customer.id for customer in pack.customers}):
        raise ValueError("cross-customer pack contains duplicate customer IDs")
    if not pack.customers:
        raise ValueError("cross-customer pack must contain at least one customer")

    dimension_values: dict[str, list[str]] = {}
    for dimension in pack.required_stress_dimensions:
        missing = [customer.id for customer in pack.customers if dimension not in customer.context]
        if missing:
            raise ValueError(f"stress dimension {dimension!r} missing for customers: {missing}")
        values = sorted({customer.context[dimension] for customer in pack.customers})
        if len(values) < 2:
            raise ValueError(
                f"stress dimension {dimension!r} does not vary across customers: {values}"
            )
        dimension_values[dimension] = values
    return dimension_values


def run_cross_customer_qualification(repo_root: Path, pack_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    pack = load_cross_customer_pack(pack_path)
    suite_path = repo_root / pack.runtime_suite
    suite = load_runtime_coverage_suite(suite_path)
    dimension_values = _validate_pack(pack, suite)

    baseline_signature = suite_semantic_signature(suite)
    baseline_signature_hash = _hash_payload(baseline_signature)
    customer_reports: list[dict[str, Any]] = []
    semantic_extension_count = 0

    for profile in pack.customers:
        profiled_cases = [_profile_case(case, profile) for case in suite.questions]
        profiled_suite = RuntimeCoverageSuite(
            id=f"{suite.id}:{profile.id}",
            version=pack.version,
            archetype_id=suite.archetype_id,
            competency_pack=suite.competency_pack,
            description=f"{suite.description} Cross-customer profile: {profile.name}.",
            questions=profiled_cases,
        )
        profiled_signature = suite_semantic_signature(profiled_suite)
        signature_hash = _hash_payload(profiled_signature)
        no_semantic_extension = profiled_signature == baseline_signature
        if not no_semantic_extension:
            semantic_extension_count += 1

        results = [
            run_runtime_question(case, profiled_suite.id, repo_root)
            for case in profiled_suite.questions
        ]
        status_counts = {
            status: sum(result["status"] == status for result in results)
            for status in ("PASS", "FAIL", "ERROR")
        }
        all_evidence_gates_pass = all(
            result["operator_evidence_gate"]["passed"] for result in results
        )
        passed = (
            no_semantic_extension
            and status_counts == {"PASS": len(results), "FAIL": 0, "ERROR": 0}
            and all_evidence_gates_pass
        )
        customer_reports.append(
            {
                "customer_id": profile.id,
                "customer_name": profile.name,
                "context": profile.context,
                "scenario_theme": profile.scenario_theme,
                "source_evidence": [item.model_dump() for item in profile.source_evidence],
                "semantic_signature_hash": signature_hash,
                "no_semantic_extension": no_semantic_extension,
                "question_count": len(results),
                "status_counts": status_counts,
                "runtime_coverage_rate": (
                    status_counts["PASS"] / len(results) if results else 0.0
                ),
                "operator_evidence_gate_pass": all_evidence_gates_pass,
                "status": "PASS" if passed else "FAIL",
                "results": results,
            }
        )

    total_questions = sum(report["question_count"] for report in customer_reports)
    total_passed = sum(report["status_counts"]["PASS"] for report in customer_reports)
    passed_customers = sum(report["status"] == "PASS" for report in customer_reports)
    return {
        "cross_customer_qualification_version": pack.version,
        "mode": "deterministic-cross-customer-runtime-qualification",
        "pack_id": pack.id,
        "pack_hash": _hash_payload(pack.model_dump(mode="json")),
        "archetype_id": pack.archetype_id,
        "competency_pack": pack.competency_pack,
        "runtime_suite": pack.runtime_suite,
        "canonical_semantic_signature_hash": baseline_signature_hash,
        "semantic_extension_count": semantic_extension_count,
        "required_stress_dimensions": pack.required_stress_dimensions,
        "stress_dimension_values": dimension_values,
        "customer_count": len(customer_reports),
        "passed_customers": passed_customers,
        "question_count_per_customer": len(suite.questions),
        "total_question_executions": total_questions,
        "total_passed_question_executions": total_passed,
        "cross_customer_runtime_coverage_rate": (
            total_passed / total_questions if total_questions else 0.0
        ),
        "status": (
            "PASS"
            if passed_customers == len(customer_reports) and semantic_extension_count == 0
            else "FAIL"
        ),
        "customers": customer_reports,
    }

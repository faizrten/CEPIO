"""Deterministic runtime-evidence coverage for CEPIO competency questions.

The semantic harness proves that CEPIO has a valid ontology composition for a business
question. This module proves that a CEPIO runtime can materialize and retrieve the
corresponding evidence pattern. It is intentionally source-neutral and archetype-neutral:
industry suites provide fixtures; this engine only enforces the runtime contract.

No LLM output participates in pass/fail. Operator answers fail closed unless every cited
evidence identifier was produced by the current CEPIO evidence bundle.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from .bootstrap import build_runtime
from .generalization import load_pack
from .model import ObjectRef, OntologyObject, Relationship
from .operational_assurance import EvidenceBundle, EvidenceRecord, OperatorAnswer, validate_operator_answer


class RuntimeObjectSpec(BaseModel):
    id: str
    type: str
    name: str
    properties: dict[str, Any] = Field(default_factory=dict)
    interfaces: set[str] = Field(default_factory=set)


class RuntimeRelationshipSpec(BaseModel):
    id: str
    type: str
    source: str
    target: str


class RuntimeProbe(BaseModel):
    id: str
    kind: Literal["relationship", "property"]
    start_id: str | None = None
    relationship_type: str | None = None
    direction: Literal["out", "in"] = "out"
    expected_ids: list[str] = Field(default_factory=list)
    object_id: str | None = None
    property_name: str | None = None
    expected_value: Any | None = None


class RuntimeQuestionCase(BaseModel):
    question_id: str
    claim: str
    capabilities: list[str] = Field(default_factory=list)
    objects: list[RuntimeObjectSpec]
    relationships: list[RuntimeRelationshipSpec] = Field(default_factory=list)
    probes: list[RuntimeProbe]


class RuntimeCoverageSuite(BaseModel):
    id: str
    version: str
    archetype_id: str
    competency_pack: str
    description: str = ""
    questions: list[RuntimeQuestionCase]


def _load_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return raw


def load_runtime_coverage_suite(path: Path) -> RuntimeCoverageSuite:
    return RuntimeCoverageSuite.model_validate(_load_yaml(path))


def _hash_payload(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _evidence_bundle(
    question_id: str,
    suite_id: str,
    answer_facts: dict[str, Any],
    records: list[EvidenceRecord],
) -> EvidenceBundle:
    payload = {
        "question_id": question_id,
        "scenario_id": suite_id,
        "answer_facts": answer_facts,
        "records": [record.model_dump(mode="json") for record in records],
    }
    return EvidenceBundle(
        question_id=question_id,
        scenario_id=suite_id,
        answer_facts=answer_facts,
        records=records,
        bundle_hash=_hash_payload(payload),
    )


def _validate_suite(suite: RuntimeCoverageSuite, repo_root: Path) -> list[str]:
    pack = load_pack(repo_root / suite.competency_pack)
    if pack.archetype_id != suite.archetype_id:
        raise ValueError(
            f"runtime suite archetype {suite.archetype_id!r} != competency archetype {pack.archetype_id!r}"
        )
    if not getattr(pack, "frozen", False):
        raise ValueError("runtime coverage must target a frozen competency pack")

    expected = [question.id for question in pack.questions]
    supplied = [question.question_id for question in suite.questions]
    if len(supplied) != len(set(supplied)):
        raise ValueError("runtime suite contains duplicate question IDs")
    missing = sorted(set(expected) - set(supplied))
    unknown = sorted(set(supplied) - set(expected))
    if missing or unknown:
        raise ValueError(f"runtime coverage mismatch: missing={missing}, unknown={unknown}")
    return expected


def _run_probe(runtime: Any, question_id: str, probe: RuntimeProbe) -> tuple[bool, dict[str, Any], EvidenceRecord]:
    if probe.kind == "relationship":
        if not probe.start_id or not probe.relationship_type:
            raise ValueError(f"{question_id}/{probe.id}: relationship probe requires start_id and relationship_type")
        if probe.direction == "out":
            resolved = runtime.neighbors(probe.start_id, probe.relationship_type)
        else:
            resolved = runtime.reverse_neighbors(probe.start_id, probe.relationship_type)
        actual = sorted({obj.id for obj in resolved})
        expected = sorted(set(probe.expected_ids))
        passed = actual == expected
        details = {
            "kind": probe.kind,
            "start_id": probe.start_id,
            "relationship_type": probe.relationship_type,
            "direction": probe.direction,
            "expected_ids": expected,
            "actual_ids": actual,
        }
    else:
        if not probe.object_id or not probe.property_name:
            raise ValueError(f"{question_id}/{probe.id}: property probe requires object_id and property_name")
        obj = runtime.get_object(probe.object_id)
        actual_value = obj.properties.get(probe.property_name)
        passed = actual_value == probe.expected_value
        details = {
            "kind": probe.kind,
            "object_id": probe.object_id,
            "property_name": probe.property_name,
            "expected_value": probe.expected_value,
            "actual_value": actual_value,
        }

    record = EvidenceRecord(
        id=f"{question_id}:probe:{probe.id}",
        kind="audit",
        payload={"passed": passed, **details},
    )
    return passed, details, record


def run_runtime_question(case: RuntimeQuestionCase, suite_id: str, repo_root: Path) -> dict[str, Any]:
    runtime = build_runtime(
        resource_root=repo_root,
        validate_types=False,
        validate_properties=False,
    )
    stored: dict[str, OntologyObject] = {}
    records: list[EvidenceRecord] = []

    for spec in case.objects:
        obj = runtime.upsert_object(
            OntologyObject(
                id=spec.id,
                type=spec.type,
                name=spec.name,
                properties=spec.properties,
                interfaces=spec.interfaces,
            )
        )
        stored[obj.id] = obj
        records.append(
            EvidenceRecord(
                id=f"{case.question_id}:object:{obj.id}",
                kind="object_snapshot",
                payload=obj.model_dump(mode="json"),
            )
        )

    for spec in case.relationships:
        if spec.source not in stored or spec.target not in stored:
            raise ValueError(
                f"{case.question_id}/{spec.id}: relationship endpoints must be declared objects"
            )
        source = stored[spec.source]
        target = stored[spec.target]
        rel = runtime.add_relationship(
            Relationship(
                type=spec.type,
                source=ObjectRef(id=source.id, type=source.type),
                target=ObjectRef(id=target.id, type=target.type),
            )
        )
        records.append(
            EvidenceRecord(
                id=f"{case.question_id}:relationship:{spec.id}",
                kind="audit",
                payload={
                    "fixture_relationship_id": spec.id,
                    "runtime_relationship_id": rel.id,
                    "type": rel.type,
                    "source": rel.source.model_dump(mode="json"),
                    "target": rel.target.model_dump(mode="json"),
                },
            )
        )

    probe_results: list[dict[str, Any]] = []
    probe_evidence_ids: list[str] = []
    all_probes_pass = True
    for probe in case.probes:
        passed, details, record = _run_probe(runtime, case.question_id, probe)
        all_probes_pass = all_probes_pass and passed
        probe_results.append({"id": probe.id, "status": "PASS" if passed else "FAIL", **details})
        records.append(record)
        probe_evidence_ids.append(record.id)

    bundle = _evidence_bundle(
        case.question_id,
        suite_id,
        {
            "claim": case.claim,
            "capabilities": case.capabilities,
            "resolved_probes": {item["id"]: item for item in probe_results},
        },
        records,
    )

    supported = validate_operator_answer(
        OperatorAnswer(
            status="ANSWERED",
            answer="Answer is constrained to the cited CEPIO runtime evidence.",
            evidence_ids=probe_evidence_ids,
        ),
        bundle,
    )
    unsupported = validate_operator_answer(
        OperatorAnswer(
            status="ANSWERED",
            answer="Unsupported runtime assertion.",
            evidence_ids=probe_evidence_ids + ["fabricated:runtime-evidence"],
        ),
        bundle,
    )
    evidence_gate_pass = (
        bool(probe_evidence_ids)
        and supported.status == "ANSWERED"
        and unsupported.status == "REJECTED_UNSUPPORTED_EVIDENCE"
    )
    passed = all_probes_pass and evidence_gate_pass

    return {
        "question_id": case.question_id,
        "status": "PASS" if passed else "FAIL",
        "claim": case.claim,
        "capabilities": case.capabilities,
        "probe_count": len(case.probes),
        "probe_results": probe_results,
        "operator_evidence_gate": {
            "supported": supported.status,
            "unsupported": unsupported.status,
            "passed": evidence_gate_pass,
        },
        "evidence_bundle": bundle.model_dump(mode="json"),
    }


def run_runtime_coverage(repo_root: Path, suite_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    suite = load_runtime_coverage_suite(suite_path)
    expected_questions = _validate_suite(suite, repo_root)

    results = [run_runtime_question(case, suite.id, repo_root) for case in suite.questions]
    status_counts = {
        status: sum(result["status"] == status for result in results)
        for status in ("PASS", "FAIL", "ERROR")
    }
    passed = status_counts["PASS"]
    return {
        "runtime_coverage_version": suite.version,
        "mode": "deterministic-runtime-evidence-coverage",
        "suite_id": suite.id,
        "suite_hash": _hash_payload(suite.model_dump(mode="json")),
        "archetype_id": suite.archetype_id,
        "competency_pack": suite.competency_pack,
        "expected_questions": expected_questions,
        "question_count": len(results),
        "status_counts": status_counts,
        "runtime_coverage_rate": passed / len(results) if results else 0.0,
        "results": results,
    }

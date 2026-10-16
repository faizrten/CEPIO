"""Deterministic operational-assurance harness for CEPIO.

This module deliberately sits beside the semantic generalization harness. Semantic
coverage proves that a business capability is representable; operational assurance
proves that CEPIO can reconstruct time, explain provenance, resolve scoped authority,
enforce policy, execute a governed action and produce auditable evidence.

LLM or agent output is never accepted as enterprise evidence. An Operator may explain
only facts that are backed by CEPIO evidence identifiers from the current bundle.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field

from .bootstrap import build_runtime
from .generalization import load_pack
from .model import ActionRequest, Decision, ObjectRef, OntologyObject, Relationship
from .property_registry import PropertyRegistry
from .provenance import (
    InMemoryProvenanceRepository,
    PropertyProvenance,
    SourceReference,
    TransformationRun,
    explain_property,
)
from .runtime import AuthorizationError
from .temporal import TemporalInMemoryRepository

CORE_VALID_FROM = "https://cepio.org/ontology/core#validFrom"
CORE_VALID_TO = "https://cepio.org/ontology/core#validTo"
WF_AUTHORITY_ASSIGNMENT = "https://cepio.org/ontology/workforce#AuthorityAssignment"
WF_CREW_MEMBER = "https://cepio.org/ontology/workforce#CrewMember"
WF_AUTHORITY_FOR_ASSET = "https://cepio.org/ontology/workforce#authorityForAsset"
WF_AUTHORITY_HOLDER = "https://cepio.org/ontology/workforce#authorityHolder"
DRILL_OPERATING_RIG = "https://cepio.org/ontology/drilling#OperatingRig"


class TemporalRuntimeCase(BaseModel):
    question_id: str
    object_id: str
    object_name: str
    object_type: str
    property_name: str
    valid_from: datetime
    valid_to: datetime
    query_valid_time: datetime
    initial_value: str
    corrected_value: str
    rationale: str = ""


class ProvenanceSourceSpec(BaseModel):
    source_system: str
    source_entity: str
    source_field: str
    source_record_id: str | None = None
    source_uri: str | None = None


class ProvenanceRuntimeCase(BaseModel):
    question_id: str
    object_id: str
    object_name: str
    object_type: str
    property_name: str
    value: float
    unit: str
    observed_at: datetime
    source: ProvenanceSourceSpec
    mapping_kind: str
    mapping_id: str
    mapping_version: str
    code_version: str | None = None
    transformation_started_at: datetime
    transformation_completed_at: datetime
    rationale: str = ""


class AuthorityRuntimeCase(BaseModel):
    question_id: str
    rig_id: str
    rig_name: str
    authority_assignment_id: str
    authority_holder_id: str
    authority_holder_name: str
    valid_from: datetime
    valid_to: datetime
    rationale: str = ""


class GovernedActionRuntimeCase(BaseModel):
    question_id: str
    target_id: str
    target_name: str
    target_type: str = "Equipment"
    interfaces: list[str] = Field(default_factory=lambda: ["Inspectable"])
    action_type: str = "CreateInspection"
    problem: str
    observations: list[str]
    recommendation: str
    ai_actor_id: str = "operator-agent-1"
    ai_actor_roles: set[str] = Field(default_factory=lambda: {"ai_agent_recommender"})
    human_actor_id: str = "reliability-engineer-1"
    human_actor_roles: set[str] = Field(default_factory=lambda: {"reliability_engineer"})
    rationale: str = ""


class OperationalScenario(BaseModel):
    id: str
    version: str
    archetype_id: str
    competency_pack: str
    description: str = ""
    temporal_case: TemporalRuntimeCase
    provenance_case: ProvenanceRuntimeCase
    authority_case: AuthorityRuntimeCase
    governed_action_case: GovernedActionRuntimeCase


EvidenceKind = Literal[
    "object_snapshot",
    "temporal_query",
    "property_provenance",
    "transformation",
    "source_reference",
    "authority_assignment",
    "authority_resolution",
    "decision",
    "policy_decision",
    "action_result",
    "audit",
]


class EvidenceRecord(BaseModel):
    id: str
    kind: EvidenceKind
    payload: dict[str, Any]


class EvidenceBundle(BaseModel):
    question_id: str
    scenario_id: str
    answer_facts: dict[str, Any]
    records: list[EvidenceRecord] = Field(default_factory=list)
    bundle_hash: str

    @property
    def evidence_ids(self) -> set[str]:
        return {record.id for record in self.records}


class OperatorAnswer(BaseModel):
    status: Literal[
        "ANSWERED",
        "INSUFFICIENT_CEPIO_EVIDENCE",
        "REJECTED_UNSUPPORTED_EVIDENCE",
    ]
    answer: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


def _load_yaml(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return raw


def load_operational_scenario(path: Path) -> OperationalScenario:
    return OperationalScenario.model_validate(_load_yaml(path))


def _hash_payload(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _bundle(
    question_id: str,
    scenario_id: str,
    answer_facts: dict[str, Any],
    records: list[EvidenceRecord],
) -> EvidenceBundle:
    payload = {
        "question_id": question_id,
        "scenario_id": scenario_id,
        "answer_facts": answer_facts,
        "records": [record.model_dump(mode="json") for record in records],
    }
    return EvidenceBundle(
        question_id=question_id,
        scenario_id=scenario_id,
        answer_facts=answer_facts,
        records=records,
        bundle_hash=_hash_payload(payload),
    )


def validate_operator_answer(answer: OperatorAnswer, evidence: EvidenceBundle) -> OperatorAnswer:
    """Fail closed if an Operator cites anything outside the CEPIO evidence bundle."""

    if answer.status != "ANSWERED":
        return answer
    cited = set(answer.evidence_ids)
    if not cited or not cited.issubset(evidence.evidence_ids):
        return OperatorAnswer(
            status="REJECTED_UNSUPPORTED_EVIDENCE",
            answer=None,
            evidence_ids=sorted(cited),
        )
    return answer


def run_temporal_case(case: TemporalRuntimeCase, scenario_id: str) -> dict[str, Any]:
    repository = TemporalInMemoryRepository()
    properties = {
        case.property_name: case.initial_value,
        CORE_VALID_FROM: case.valid_from.isoformat(),
        CORE_VALID_TO: case.valid_to.isoformat(),
    }
    first = repository.upsert_object(
        OntologyObject(
            id=case.object_id,
            type=case.object_type,
            name=case.object_name,
            properties=properties,
        )
    )
    first_tx = repository.object_history(case.object_id)[-1].transaction_time

    corrected_properties = dict(properties)
    corrected_properties[case.property_name] = case.corrected_value
    second = repository.upsert_object(
        OntologyObject(
            id=case.object_id,
            type=case.object_type,
            name=case.object_name,
            properties=corrected_properties,
        ),
        expected_version=first.version,
    )
    second_tx = repository.object_history(case.object_id)[-1].transaction_time

    believed_initially = repository.get_object_valid_at(
        case.object_id,
        case.query_valid_time,
        as_of_transaction=first_tx,
    )
    believed_after_correction = repository.get_object_valid_at(
        case.object_id,
        case.query_valid_time,
        as_of_transaction=second_tx,
    )
    initial_value = believed_initially.properties.get(case.property_name) if believed_initially else None
    corrected_value = believed_after_correction.properties.get(case.property_name) if believed_after_correction else None
    passed = (
        initial_value == case.initial_value
        and corrected_value == case.corrected_value
        and second.version == 2
        and second_tx >= first_tx
    )

    records = [
        EvidenceRecord(
            id=f"{case.question_id}:snapshot:1",
            kind="object_snapshot",
            payload={
                "object_id": case.object_id,
                "version": first.version,
                "transaction_time": first_tx,
                "valid_from": case.valid_from,
                "valid_to": case.valid_to,
                "property": case.property_name,
                "value": case.initial_value,
            },
        ),
        EvidenceRecord(
            id=f"{case.question_id}:snapshot:2",
            kind="object_snapshot",
            payload={
                "object_id": case.object_id,
                "version": second.version,
                "transaction_time": second_tx,
                "valid_from": case.valid_from,
                "valid_to": case.valid_to,
                "property": case.property_name,
                "value": case.corrected_value,
            },
        ),
        EvidenceRecord(
            id=f"{case.question_id}:query:initial-belief",
            kind="temporal_query",
            payload={
                "valid_time": case.query_valid_time,
                "as_of_transaction": first_tx,
                "result": initial_value,
            },
        ),
        EvidenceRecord(
            id=f"{case.question_id}:query:corrected-belief",
            kind="temporal_query",
            payload={
                "valid_time": case.query_valid_time,
                "as_of_transaction": second_tx,
                "result": corrected_value,
            },
        ),
    ]
    evidence = _bundle(
        case.question_id,
        scenario_id,
        {
            "valid_time": case.query_valid_time,
            "belief_at_first_transaction": initial_value,
            "belief_after_correction": corrected_value,
            "first_transaction_time": first_tx,
            "second_transaction_time": second_tx,
        },
        records,
    )
    return {
        "question_id": case.question_id,
        "dimension": "temporal",
        "status": "PASS" if passed else "FAIL",
        "check": "bitemporal-state-reconstruction",
        "details": {
            "initial_value": initial_value,
            "corrected_value": corrected_value,
            "object_version": second.version,
        },
        "evidence_bundle": evidence.model_dump(mode="json"),
    }


def run_provenance_case(
    case: ProvenanceRuntimeCase,
    scenario_id: str,
    repo_root: Path,
) -> dict[str, Any]:
    registry = PropertyRegistry.from_yaml(repo_root / "mappings" / "canonical_properties.yaml")
    repository = InMemoryProvenanceRepository()
    transformation = TransformationRun(
        id=f"{case.question_id}:transformation",
        mapping_id=case.mapping_id,
        mapping_version=case.mapping_version,
        code_version=case.code_version,
        started_at=case.transformation_started_at,
        completed_at=case.transformation_completed_at,
        inputs={"source_record_id": case.source.source_record_id},
        metadata={"scenario": scenario_id},
    )
    repository.add_transformation(transformation)
    source = SourceReference(**case.source.model_dump())
    provenance = PropertyProvenance.create(
        object_id=case.object_id,
        property_name=case.property_name,
        property_registry=registry,
        source=source,
        mapping_kind=case.mapping_kind,
        mapping_version=case.mapping_version,
        observed_at=case.observed_at,
        transformation_id=transformation.id,
        source_value=case.value,
    )
    repository.append_property(provenance)
    explanation = explain_property(case.object_id, case.property_name, registry, repository)

    records = explanation["provenance"]
    transformations = explanation["transformations"]
    resolved = registry.resolve(case.property_name)
    passed = (
        len(records) == 1
        and records[0]["source"]["source_system"] == case.source.source_system
        and records[0]["source"]["source_field"] == case.source.source_field
        and records[0]["observed_at"] == case.observed_at
        and records[0]["mapping_version"] == case.mapping_version
        and records[0]["transformation_id"] == transformation.id
        and transformation.id in transformations
        and transformations[transformation.id]["mapping_id"] == case.mapping_id
        and transformations[transformation.id]["mapping_version"] == case.mapping_version
    )

    evidence_records = [
        EvidenceRecord(
            id=f"{case.question_id}:source",
            kind="source_reference",
            payload=source.model_dump(mode="json"),
        ),
        EvidenceRecord(
            id=f"{case.question_id}:provenance",
            kind="property_provenance",
            payload=provenance.model_dump(mode="json"),
        ),
        EvidenceRecord(
            id=f"{case.question_id}:transformation",
            kind="transformation",
            payload=transformation.model_dump(mode="json"),
        ),
    ]
    evidence = _bundle(
        case.question_id,
        scenario_id,
        {
            "object_id": case.object_id,
            "property_iri": resolved.iri,
            "value": case.value,
            "unit": case.unit,
            "source_system": case.source.source_system,
            "source_record_id": case.source.source_record_id,
            "observed_at": case.observed_at,
            "mapping_id": case.mapping_id,
            "mapping_version": case.mapping_version,
            "transformation_id": transformation.id,
        },
        evidence_records,
    )
    return {
        "question_id": case.question_id,
        "dimension": "provenance",
        "status": "PASS" if passed else "FAIL",
        "check": "property-provenance-and-transformation",
        "details": {
            "source_system": case.source.source_system,
            "mapping_version": case.mapping_version,
            "transformation_id": transformation.id,
        },
        "evidence_bundle": evidence.model_dump(mode="json"),
    }


def run_authority_case(
    case: AuthorityRuntimeCase,
    scenario_id: str,
    repo_root: Path,
) -> dict[str, Any]:
    runtime = build_runtime(
        resource_root=repo_root,
        validate_types=False,
        validate_properties=False,
    )
    rig = runtime.upsert_object(
        OntologyObject(id=case.rig_id, type=DRILL_OPERATING_RIG, name=case.rig_name)
    )
    holder = runtime.upsert_object(
        OntologyObject(
            id=case.authority_holder_id,
            type=WF_CREW_MEMBER,
            name=case.authority_holder_name,
        )
    )
    assignment = runtime.upsert_object(
        OntologyObject(
            id=case.authority_assignment_id,
            type=WF_AUTHORITY_ASSIGNMENT,
            name=f"Authority assignment for {case.rig_name}",
            properties={
                CORE_VALID_FROM: case.valid_from.isoformat(),
                CORE_VALID_TO: case.valid_to.isoformat(),
            },
        )
    )
    runtime.add_relationship(
        Relationship(
            type=WF_AUTHORITY_FOR_ASSET,
            source=ObjectRef(id=assignment.id, type=assignment.type),
            target=ObjectRef(id=rig.id, type=rig.type),
        )
    )
    runtime.add_relationship(
        Relationship(
            type=WF_AUTHORITY_HOLDER,
            source=ObjectRef(id=assignment.id, type=assignment.type),
            target=ObjectRef(id=holder.id, type=holder.type),
        )
    )

    assignments = runtime.reverse_neighbors(rig.id, WF_AUTHORITY_FOR_ASSET)
    holders = []
    for item in assignments:
        holders.extend(runtime.neighbors(item.id, WF_AUTHORITY_HOLDER))
    resolved_ids = sorted({item.id for item in holders})
    passed = (
        [item.id for item in assignments] == [case.authority_assignment_id]
        and resolved_ids == [case.authority_holder_id]
    )

    records = [
        EvidenceRecord(
            id=f"{case.question_id}:authority-assignment",
            kind="authority_assignment",
            payload=assignment.model_dump(mode="json"),
        ),
        EvidenceRecord(
            id=f"{case.question_id}:authority-resolution",
            kind="authority_resolution",
            payload={
                "rig_id": rig.id,
                "assignment_ids": [item.id for item in assignments],
                "authority_holder_ids": resolved_ids,
                "valid_from": case.valid_from,
                "valid_to": case.valid_to,
            },
        ),
    ]
    evidence = _bundle(
        case.question_id,
        scenario_id,
        {
            "rig_id": rig.id,
            "authority_assignment_id": assignment.id,
            "authority_holder_id": holder.id,
            "authority_holder_name": holder.name,
            "valid_from": case.valid_from,
            "valid_to": case.valid_to,
        },
        records,
    )
    return {
        "question_id": case.question_id,
        "dimension": "authority",
        "status": "PASS" if passed else "FAIL",
        "check": "scoped-authority-resolution",
        "details": {
            "authority_holder_id": case.authority_holder_id,
            "resolved_holder_ids": resolved_ids,
        },
        "evidence_bundle": evidence.model_dump(mode="json"),
    }


def _enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def run_governed_action_case(
    case: GovernedActionRuntimeCase,
    scenario_id: str,
    repo_root: Path,
) -> dict[str, Any]:
    runtime = build_runtime(
        resource_root=repo_root,
        validate_types=False,
        validate_properties=False,
    )
    target = runtime.upsert_object(
        OntologyObject(
            id=case.target_id,
            type=case.target_type,
            name=case.target_name,
            interfaces=set(case.interfaces),
            properties={"criticality": "high", "operatingState": "degraded"},
        )
    )
    decision = runtime.save_decision(
        Decision(
            subject=ObjectRef(id=target.id, type=target.type),
            problem=case.problem,
            observations=case.observations,
            recommendation=case.recommendation,
            recommended_action=case.action_type,
            confidence=0.9,
            created_by=case.ai_actor_id,
        )
    )

    ai_request = ActionRequest(
        action_type=case.action_type,
        target=ObjectRef(id=target.id, type=target.type),
        actor_id=case.ai_actor_id,
        actor_roles=case.ai_actor_roles,
        decision_id=decision.id,
        idempotency_key=f"{case.question_id}:agent-attempt",
    )
    ai_result = None
    try:
        ai_result = runtime.execute_action(ai_request)
    except AuthorizationError as exc:
        ai_result = exc.result
    if ai_result is None:
        raise RuntimeError("governed action case did not produce an AI action result")
    ai_audit = runtime.all_audits()[-1]

    human_request = ActionRequest(
        action_type=case.action_type,
        target=ObjectRef(id=target.id, type=target.type),
        actor_id=case.human_actor_id,
        actor_roles=case.human_actor_roles,
        decision_id=decision.id,
        idempotency_key=f"{case.question_id}:human-attempt",
    )
    human_result = runtime.execute_action(human_request)
    human_audit = runtime.all_audits()[-1]

    ai_policy_effect = _enum_value(ai_audit.policy_effect)
    human_policy_effect = _enum_value(human_audit.policy_effect)
    passed = (
        _enum_value(ai_result.status) == "rejected"
        and ai_policy_effect == "recommend_only"
        and _enum_value(human_result.status) == "executed"
        and human_policy_effect == "allow"
        and human_audit.decision_id == decision.id
        and human_result.audit_id == human_audit.id
    )

    records = [
        EvidenceRecord(
            id=f"{case.question_id}:decision",
            kind="decision",
            payload=decision.model_dump(mode="json"),
        ),
        EvidenceRecord(
            id=f"{case.question_id}:agent-policy",
            kind="policy_decision",
            payload={
                "actor_id": case.ai_actor_id,
                "actor_roles": sorted(case.ai_actor_roles),
                "effect": ai_policy_effect,
                "reasons": ai_audit.policy_reasons,
            },
        ),
        EvidenceRecord(
            id=f"{case.question_id}:agent-audit",
            kind="audit",
            payload=ai_audit.model_dump(mode="json"),
        ),
        EvidenceRecord(
            id=f"{case.question_id}:human-action",
            kind="action_result",
            payload=human_result.model_dump(mode="json"),
        ),
        EvidenceRecord(
            id=f"{case.question_id}:human-audit",
            kind="audit",
            payload=human_audit.model_dump(mode="json"),
        ),
    ]
    evidence = _bundle(
        case.question_id,
        scenario_id,
        {
            "decision_id": decision.id,
            "recommended_action": decision.recommended_action,
            "agent_policy_effect": ai_policy_effect,
            "agent_action_status": _enum_value(ai_result.status),
            "human_policy_effect": human_policy_effect,
            "human_action_status": _enum_value(human_result.status),
            "human_audit_id": human_audit.id,
        },
        records,
    )
    return {
        "question_id": case.question_id,
        "dimension": "policy+kinetic",
        "status": "PASS" if passed else "FAIL",
        "check": "recommend-only-agent-to-authorized-human-action",
        "details": {
            "agent_action_status": _enum_value(ai_result.status),
            "agent_policy_effect": ai_policy_effect,
            "human_action_status": _enum_value(human_result.status),
            "human_policy_effect": human_policy_effect,
            "decision_id": decision.id,
            "audit_id": human_audit.id,
        },
        "evidence_bundle": evidence.model_dump(mode="json"),
    }


def run_operator_evidence_gate(
    question_id: str,
    scenario_id: str,
    evidence: EvidenceBundle,
) -> dict[str, Any]:
    supported_id = sorted(evidence.evidence_ids)[0]
    supported = validate_operator_answer(
        OperatorAnswer(
            status="ANSWERED",
            answer="CEPIO can answer this claim from the cited runtime evidence.",
            evidence_ids=[supported_id],
        ),
        evidence,
    )
    unsupported = validate_operator_answer(
        OperatorAnswer(
            status="ANSWERED",
            answer="This answer cites evidence that CEPIO never produced.",
            evidence_ids=["fabricated:evidence"],
        ),
        evidence,
    )
    passed = (
        supported.status == "ANSWERED"
        and unsupported.status == "REJECTED_UNSUPPORTED_EVIDENCE"
    )
    gate_evidence = _bundle(
        question_id,
        scenario_id,
        {
            "supported_answer_status": supported.status,
            "unsupported_answer_status": unsupported.status,
            "supported_evidence_id": supported_id,
        },
        [
            EvidenceRecord(
                id=f"{question_id}:operator-evidence-gate",
                kind="audit",
                payload={
                    "supported_answer": supported.model_dump(mode="json"),
                    "unsupported_answer": unsupported.model_dump(mode="json"),
                    "source_bundle_hash": evidence.bundle_hash,
                },
            )
        ],
    )
    return {
        "question_id": question_id,
        "dimension": "operator-evidence",
        "status": "PASS" if passed else "FAIL",
        "check": "operator-citation-fail-closed",
        "details": {
            "supported_answer_status": supported.status,
            "unsupported_answer_status": unsupported.status,
        },
        "evidence_bundle": gate_evidence.model_dump(mode="json"),
    }


def _validate_question_ids(
    scenario: OperationalScenario,
    repo_root: Path,
) -> list[str]:
    competency_path = repo_root / scenario.competency_pack
    pack = load_pack(competency_path)
    if pack.archetype_id != scenario.archetype_id:
        raise ValueError(
            f"operational scenario archetype {scenario.archetype_id!r} != competency archetype {pack.archetype_id!r}"
        )
    question_ids = {question.id for question in pack.questions}
    referenced = [
        scenario.temporal_case.question_id,
        scenario.provenance_case.question_id,
        scenario.authority_case.question_id,
        scenario.governed_action_case.question_id,
    ]
    unknown = sorted(set(referenced) - question_ids)
    if unknown:
        raise ValueError(f"operational scenario references unknown competency questions: {unknown}")
    return referenced


def run_operational_assurance(repo_root: Path, scenario_path: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    scenario = load_operational_scenario(scenario_path)
    referenced_questions = _validate_question_ids(scenario, repo_root)

    temporal = run_temporal_case(scenario.temporal_case, scenario.id)
    provenance = run_provenance_case(scenario.provenance_case, scenario.id, repo_root)
    authority = run_authority_case(scenario.authority_case, scenario.id, repo_root)
    governed = run_governed_action_case(scenario.governed_action_case, scenario.id, repo_root)
    governed_bundle = EvidenceBundle.model_validate(governed["evidence_bundle"])
    operator = run_operator_evidence_gate(
        scenario.governed_action_case.question_id,
        scenario.id,
        governed_bundle,
    )
    results = [temporal, provenance, authority, governed, operator]

    status_counts = {
        status: sum(result["status"] == status for result in results)
        for status in ("PASS", "FAIL", "ERROR")
    }
    dimension_status = {result["dimension"]: result["status"] for result in results}
    passed = status_counts["PASS"]
    return {
        "assurance_version": "0.4",
        "mode": "deterministic-operational-assurance",
        "scenario_id": scenario.id,
        "scenario_hash": _hash_payload(scenario.model_dump(mode="json")),
        "archetype_id": scenario.archetype_id,
        "competency_pack": scenario.competency_pack,
        "referenced_questions": referenced_questions,
        "gate_count": len(results),
        "status_counts": status_counts,
        "dimension_status": dimension_status,
        "assurance_pass_rate": passed / len(results),
        "results": results,
    }

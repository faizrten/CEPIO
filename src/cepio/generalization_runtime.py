from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Protocol

import yaml
from pydantic import BaseModel, Field

from .model import OntologyObject
from .property_registry import PropertyRegistry
from .provenance import (
    InMemoryProvenanceRepository,
    PropertyProvenance,
    SourceReference,
    TransformationRun,
    explain_property,
)
from .temporal import TemporalInMemoryRepository

CORE_VALID_FROM = "https://cepio.org/ontology/core#validFrom"
CORE_VALID_TO = "https://cepio.org/ontology/core#validTo"


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


class RuntimeScenario(BaseModel):
    id: str
    version: str
    archetype_id: str
    description: str = ""
    temporal_case: TemporalRuntimeCase
    provenance_case: ProvenanceRuntimeCase


class EvidenceRecord(BaseModel):
    id: str
    kind: Literal[
        "object_snapshot",
        "temporal_query",
        "property_provenance",
        "transformation",
        "source_reference",
    ]
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


class OperatorPlanner(Protocol):
    """Platform-neutral planner contract for a future LLM-backed Operator.

    Implementations receive only the frozen question and CEPIO evidence bundle. The
    harness validates every cited evidence id before accepting the answer.
    """

    def answer(self, question: str, evidence: EvidenceBundle) -> OperatorAnswer: ...


def validate_operator_answer(answer: OperatorAnswer, evidence: EvidenceBundle) -> OperatorAnswer:
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


def _load_yaml(path: Path) -> dict:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return raw


def load_runtime_scenario(path: Path) -> RuntimeScenario:
    return RuntimeScenario.model_validate(_load_yaml(path))


def _hash_payload(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _bundle(question_id: str, scenario_id: str, answer_facts: dict[str, Any], records: list[EvidenceRecord]) -> EvidenceBundle:
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
    first_history = repository.object_history(case.object_id)
    first_tx = first_history[-1].transaction_time

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
    history = repository.object_history(case.object_id)
    second_tx = history[-1].transaction_time

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
        "status": "PASS" if passed else "FAIL",
        "check": "bitemporal-state-reconstruction",
        "evidence_bundle": evidence.model_dump(mode="json"),
    }


def run_provenance_case(case: ProvenanceRuntimeCase, scenario_id: str, repo_root: Path) -> dict[str, Any]:
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
        "status": "PASS" if passed else "FAIL",
        "check": "property-provenance-and-transformation",
        "evidence_bundle": evidence.model_dump(mode="json"),
    }


def run_runtime_scenario(repo_root: Path, scenario_path: Path) -> dict[str, Any]:
    scenario = load_runtime_scenario(scenario_path)
    results = [
        run_temporal_case(scenario.temporal_case, scenario.id),
        run_provenance_case(scenario.provenance_case, scenario.id, repo_root),
    ]
    status_counts = {status: sum(r["status"] == status for r in results) for status in ("PASS", "FAIL", "ERROR")}
    return {
        "runtime_harness_version": "0.2",
        "scenario_id": scenario.id,
        "scenario_hash": _hash_payload(scenario.model_dump(mode="json")),
        "status_counts": status_counts,
        "results": results,
    }

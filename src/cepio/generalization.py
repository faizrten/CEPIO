"""Deterministic semantic-readiness harness for CEPIO generalization tests.

v0.1 intentionally evaluates ontology prerequisites only. Agentic question
generation and judging are specified separately; they are not trusted as evidence.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from rdflib import Graph, RDF, RDFS, OWL, URIRef


class TermRequirement(BaseModel):
    iri: str
    kind: Literal["class", "object_property", "datatype_property", "any"] = "any"


class EdgeRequirement(BaseModel):
    source: str
    predicate: str
    target: str


class RuntimeRequirements(BaseModel):
    temporal: bool = False
    provenance: bool = False
    policy: bool = False
    kinetic: bool = False

    @property
    def required(self) -> bool:
        return any((self.temporal, self.provenance, self.policy, self.kinetic))


class CompetencyQuestion(BaseModel):
    id: str
    question: str
    scope: str = "domain"
    priority: Literal["critical", "required", "advanced"] = "required"
    personas: list[str] = Field(default_factory=list)
    standards: list[str] = Field(default_factory=list)
    capability_tags: list[str] = Field(default_factory=list)
    terms: list[TermRequirement] = Field(default_factory=list)
    edges: list[EdgeRequirement] = Field(default_factory=list)
    runtime: RuntimeRequirements = Field(default_factory=RuntimeRequirements)


class CompetencyPack(BaseModel):
    id: str
    version: str
    archetype_id: str
    frozen: bool
    questions: list[CompetencyQuestion]


class Archetype(BaseModel):
    id: str
    version: str
    name: str
    description: str
    operating_context: list[str] = Field(default_factory=list)
    source_landscape: list[str] = Field(default_factory=list)
    scenario_seeds: list[str] = Field(default_factory=list)


class Persona(BaseModel):
    id: str
    role: str
    objectives: list[str]
    information_needs: list[str]


class PersonaPack(BaseModel):
    id: str
    version: str
    personas: list[Persona]


class StandardReference(BaseModel):
    id: str
    name: str
    body: str
    url: str
    use: str
    access: str


class StandardsRegistry(BaseModel):
    id: str
    version: str
    references: list[StandardReference]


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return value


def load_pack(path: Path) -> CompetencyPack:
    return CompetencyPack.model_validate(_load_yaml(path))


def load_archetype(path: Path) -> Archetype:
    return Archetype.model_validate(_load_yaml(path))


def load_personas(path: Path) -> PersonaPack:
    return PersonaPack.model_validate(_load_yaml(path))


def load_standards(path: Path) -> StandardsRegistry:
    return StandardsRegistry.model_validate(_load_yaml(path))


def stable_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class OntologyIndex:
    def __init__(self, graph: Graph, digest: str):
        self.graph = graph
        self.digest = digest

    @classmethod
    def from_repo(cls, repo_root: Path) -> "OntologyIndex":
        graph = Graph()
        digest = hashlib.sha256()
        paths = sorted((repo_root / "ontologies").glob("*.ttl"))
        if not paths:
            raise ValueError("no CEPIO ontology modules found")
        for path in paths:
            data = path.read_bytes()
            digest.update(path.name.encode("utf-8"))
            digest.update(b"\0")
            digest.update(data)
            graph.parse(data=data.decode("utf-8"), format="turtle")
        return cls(graph, digest.hexdigest())

    def _typed(self, iri: str, rdf_type: URIRef) -> bool:
        return (URIRef(iri), RDF.type, rdf_type) in self.graph

    def has_term(self, requirement: TermRequirement) -> bool:
        iri = URIRef(requirement.iri)
        if requirement.kind == "class":
            return self._typed(requirement.iri, OWL.Class)
        if requirement.kind == "object_property":
            return self._typed(requirement.iri, OWL.ObjectProperty)
        if requirement.kind == "datatype_property":
            return self._typed(requirement.iri, OWL.DatatypeProperty)
        return any(True for _ in self.graph.triples((iri, None, None))) or any(
            True for _ in self.graph.triples((None, None, iri))
        )

    def is_subclass_or_same(self, child: str, parent: str) -> bool:
        if child == parent:
            return True
        target = URIRef(parent)
        seen: set[URIRef] = set()
        stack = [URIRef(child)]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            for candidate in self.graph.objects(current, RDFS.subClassOf):
                if candidate == target:
                    return True
                if isinstance(candidate, URIRef):
                    stack.append(candidate)
        return False

    def has_edge_contract(self, requirement: EdgeRequirement) -> bool:
        predicate = URIRef(requirement.predicate)
        if (predicate, RDF.type, OWL.ObjectProperty) not in self.graph:
            return False
        domains = [str(x) for x in self.graph.objects(predicate, RDFS.domain) if isinstance(x, URIRef)]
        ranges = [str(x) for x in self.graph.objects(predicate, RDFS.range) if isinstance(x, URIRef)]
        domain_ok = not domains or any(self.is_subclass_or_same(requirement.source, x) for x in domains)
        range_ok = not ranges or any(self.is_subclass_or_same(requirement.target, x) for x in ranges)
        return domain_ok and range_ok


def validate_cross_references(
    pack: CompetencyPack, archetype: Archetype, personas: PersonaPack, standards: StandardsRegistry
) -> None:
    if pack.archetype_id != archetype.id:
        raise ValueError(f"pack archetype {pack.archetype_id!r} != {archetype.id!r}")
    if not pack.frozen:
        raise ValueError("competency pack must be frozen before execution")
    persona_ids = {p.id for p in personas.personas}
    standard_ids = {s.id for s in standards.references}
    unknown_personas = sorted({p for q in pack.questions for p in q.personas if p not in persona_ids})
    unknown_standards = sorted({s for q in pack.questions for s in q.standards if s not in standard_ids})
    if unknown_personas:
        raise ValueError(f"unknown persona ids: {unknown_personas}")
    if unknown_standards:
        raise ValueError(f"unknown standards ids: {unknown_standards}")


def evaluate_question(question: CompetencyQuestion, ontology: OntologyIndex) -> dict:
    checks: list[dict] = []
    for requirement in question.terms:
        ok = ontology.has_term(requirement)
        checks.append({"kind": "term", "id": requirement.iri, "ok": ok})
    for requirement in question.edges:
        ok = ontology.has_edge_contract(requirement)
        checks.append({
            "kind": "edge",
            "id": f"{requirement.source} --{requirement.predicate}--> {requirement.target}",
            "ok": ok,
        })
    passed = sum(1 for check in checks if check["ok"])
    total = len(checks)
    if total == 0:
        status = "ERROR"
    elif passed == total:
        status = "PASS"
    elif passed == 0:
        status = "FAIL"
    else:
        status = "PARTIAL"
    missing = [check["id"] for check in checks if not check["ok"]]
    return {
        "id": question.id,
        "question": question.question,
        "priority": question.priority,
        "status": status,
        "checks_passed": passed,
        "checks_total": total,
        "missing": missing,
        "runtime_status": "NOT_RUN" if question.runtime.required else "NOT_REQUIRED",
        "runtime_requirements": question.runtime.model_dump(),
    }


def run_harness(
    repo_root: Path,
    archetype_path: Path,
    competency_path: Path,
    persona_path: Path,
    standards_path: Path,
) -> dict:
    archetype = load_archetype(archetype_path)
    pack = load_pack(competency_path)
    personas = load_personas(persona_path)
    standards = load_standards(standards_path)
    validate_cross_references(pack, archetype, personas, standards)
    ontology = OntologyIndex.from_repo(repo_root)

    frozen_payload = {
        "archetype": archetype.model_dump(mode="json"),
        "competency_pack": pack.model_dump(mode="json"),
        "personas": personas.model_dump(mode="json"),
        "standards": standards.model_dump(mode="json"),
    }
    results = [evaluate_question(question, ontology) for question in pack.questions]
    total_checks = sum(result["checks_total"] for result in results)
    passed_checks = sum(result["checks_passed"] for result in results)
    statuses = {status: sum(result["status"] == status for result in results) for status in ("PASS", "PARTIAL", "FAIL", "ERROR")}
    return {
        "harness_version": "0.1",
        "mode": "deterministic-ontology-semantic-readiness",
        "archetype_id": archetype.id,
        "competency_pack_id": pack.id,
        "batch_hash": stable_hash(frozen_payload),
        "ontology_hash": ontology.digest,
        "question_count": len(results),
        "status_counts": statuses,
        "semantic_check_pass_rate": (passed_checks / total_checks) if total_checks else 0.0,
        "runtime_evaluation": "not executed in v0.1",
        "results": results,
    }

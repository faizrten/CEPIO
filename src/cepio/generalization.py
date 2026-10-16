"""CEPIO Generalization & Competency Harness.

v0.1 established deterministic ontology-semantic readiness. v0.2 adds deterministic
runtime evidence for frozen competency questions while preserving the rule that LLM
reasoning is never treated as enterprise evidence.
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


GapDisposition = Literal["CORE", "DOMAIN", "PROFILE", "MAPPING", "REJECT"]
GapBenchmarkAction = Literal[
    "candidate-v0.2-remediation",
    "retain-v0.1-gap",
    "revise-in-next-frozen-pack",
]


class GapDecision(BaseModel):
    id: str
    question_id: str
    missing_semantics: list[str]
    disposition: GapDisposition
    replacement_layer: GapDisposition | None = None
    owner_module: str
    standards: list[str] = Field(default_factory=list)
    rationale: str
    proposed_resolution: str
    benchmark_action: GapBenchmarkAction


class GapTriagePack(BaseModel):
    id: str
    version: str
    archetype_id: str
    competency_pack_id: str
    status: Literal["draft", "accepted"]
    classification_policy: dict[str, str]
    decisions: list[GapDecision]


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


def load_gap_triage(path: Path) -> GapTriagePack:
    return GapTriagePack.model_validate(_load_yaml(path))


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


def validate_gap_triage(
    pack: CompetencyPack,
    archetype: Archetype,
    standards: StandardsRegistry,
    triage: GapTriagePack,
    results: list[dict],
) -> None:
    if triage.status != "accepted":
        raise ValueError("gap triage must be accepted before it is used by the executable harness")
    if triage.archetype_id != archetype.id:
        raise ValueError(f"gap triage archetype {triage.archetype_id!r} != {archetype.id!r}")
    if triage.competency_pack_id != pack.id:
        raise ValueError(f"gap triage competency pack {triage.competency_pack_id!r} != {pack.id!r}")

    question_ids = {q.id for q in pack.questions}
    standard_ids = {s.id for s in standards.references}
    unknown_questions = sorted({d.question_id for d in triage.decisions if d.question_id not in question_ids})
    unknown_standards = sorted({s for d in triage.decisions for s in d.standards if s not in standard_ids})
    if unknown_questions:
        raise ValueError(f"gap triage references unknown question ids: {unknown_questions}")
    if unknown_standards:
        raise ValueError(f"gap triage references unknown standards ids: {unknown_standards}")

    expected = {
        (result["id"], missing)
        for result in results
        if result["status"] in {"PARTIAL", "FAIL"}
        for missing in result["missing"]
    }
    covered: set[tuple[str, str]] = set()
    duplicates: set[tuple[str, str]] = set()
    for decision in triage.decisions:
        for missing in decision.missing_semantics:
            key = (decision.question_id, missing)
            if key in covered:
                duplicates.add(key)
            covered.add(key)

    if duplicates:
        raise ValueError(f"gap triage contains duplicate coverage: {sorted(duplicates)}")
    untriaged = sorted(expected - covered)
    stale = sorted(covered - expected)
    if untriaged:
        raise ValueError(f"current semantic gaps are not triaged: {untriaged}")
    if stale:
        raise ValueError(f"gap triage contains stale/non-current gaps: {stale}")


def _apply_runtime_results(results: list[dict], runtime_report: dict) -> None:
    runtime_by_question = {item["question_id"]: item for item in runtime_report["results"]}
    for result in results:
        if result["runtime_status"] == "NOT_REQUIRED":
            continue
        runtime = runtime_by_question.get(result["id"])
        if runtime is None:
            result["runtime_status"] = "NOT_RUN"
            continue
        result["runtime_status"] = runtime["status"]
        result["runtime_check"] = runtime["check"]
        result["evidence_bundle"] = runtime["evidence_bundle"]


def run_harness(
    repo_root: Path,
    archetype_path: Path,
    competency_path: Path,
    persona_path: Path,
    standards_path: Path,
    gap_triage_path: Path | None = None,
    runtime_scenario_path: Path | None = None,
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

    triage_hash = None
    gap_disposition_counts = {key: 0 for key in ("CORE", "DOMAIN", "PROFILE", "MAPPING", "REJECT")}
    if gap_triage_path is not None:
        triage = load_gap_triage(gap_triage_path)
        validate_gap_triage(pack, archetype, standards, triage, results)
        triage_hash = stable_hash(triage.model_dump(mode="json"))
        decisions_by_question: dict[str, list[dict]] = {}
        for decision in triage.decisions:
            gap_disposition_counts[decision.disposition] += 1
            decisions_by_question.setdefault(decision.question_id, []).append(decision.model_dump(mode="json"))
        for result in results:
            result["gap_decisions"] = decisions_by_question.get(result["id"], [])

    runtime_report = None
    if runtime_scenario_path is not None:
        from .generalization_runtime import run_runtime_scenario

        runtime_report = run_runtime_scenario(repo_root, runtime_scenario_path)
        if runtime_report["archetype_id"] != archetype.id:
            raise ValueError(
                f"runtime scenario archetype {runtime_report['archetype_id']!r} != {archetype.id!r}"
            )
        _apply_runtime_results(results, runtime_report)

    total_checks = sum(result["checks_total"] for result in results)
    passed_checks = sum(result["checks_passed"] for result in results)
    statuses = {status: sum(result["status"] == status for result in results) for status in ("PASS", "PARTIAL", "FAIL", "ERROR")}
    runtime_statuses = {
        status: sum(result["runtime_status"] == status for result in results)
        for status in ("PASS", "FAIL", "NOT_RUN", "NOT_REQUIRED")
    }
    return {
        "harness_version": "0.2" if runtime_report else "0.1",
        "mode": "semantic-readiness+runtime-evidence" if runtime_report else "deterministic-ontology-semantic-readiness",
        "archetype_id": archetype.id,
        "competency_pack_id": pack.id,
        "batch_hash": stable_hash(frozen_payload),
        "ontology_hash": ontology.digest,
        "gap_triage_hash": triage_hash,
        "gap_disposition_counts": gap_disposition_counts,
        "question_count": len(results),
        "status_counts": statuses,
        "semantic_check_pass_rate": (passed_checks / total_checks) if total_checks else 0.0,
        "runtime_status_counts": runtime_statuses,
        "runtime_scenario": runtime_report,
        "runtime_evaluation": (
            "deterministic runtime evidence executed"
            if runtime_report
            else "not executed in v0.1"
        ),
        "results": results,
    }

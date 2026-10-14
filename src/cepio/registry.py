from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rdflib import Graph, OWL, RDF, RDFS, URIRef


@dataclass
class RelationshipConstraint:
    domains: set[str] = field(default_factory=set)
    ranges: set[str] = field(default_factory=set)


@dataclass
class TypeRegistry:
    object_types: set[str] = field(default_factory=set)
    relationship_types: set[str] = field(default_factory=set)
    parents: dict[str, set[str]] = field(default_factory=dict)
    relationship_constraints: dict[str, RelationshipConstraint] = field(default_factory=dict)

    @classmethod
    def from_ontology_dir(cls, ontology_dir: str | Path) -> "TypeRegistry":
        graph = Graph()
        for path in sorted(Path(ontology_dir).glob("*.ttl")):
            graph.parse(path, format="turtle")

        registry = cls()
        for subject in graph.subjects(RDF.type, OWL.Class):
            registry.object_types.add(_local_name(subject))
        for subject, parent in graph.subject_objects(RDFS.subClassOf):
            registry.parents.setdefault(_local_name(subject), set()).add(_local_name(parent))
        for subject in graph.subjects(RDF.type, OWL.ObjectProperty):
            name = _local_name(subject)
            registry.relationship_types.add(name)
            constraint = registry.relationship_constraints.setdefault(name, RelationshipConstraint())
            for domain in graph.objects(subject, RDFS.domain):
                constraint.domains.add(_local_name(domain))
            for range_ in graph.objects(subject, RDFS.range):
                constraint.ranges.add(_local_name(range_))
        return registry

    def is_declared_type(self, type_name: str) -> bool:
        return type_name in self.object_types

    def is_declared_relationship(self, relationship_type: str) -> bool:
        return relationship_type in self.relationship_types

    def is_a(self, type_name: str, expected_type: str) -> bool:
        if type_name == expected_type:
            return True
        seen: set[str] = set()
        stack = [type_name]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            for parent in self.parents.get(current, set()):
                if parent == expected_type:
                    return True
                stack.append(parent)
        return False

    def validate_relationship_types(self, relationship_type: str, source_type: str, target_type: str) -> None:
        constraint = self.relationship_constraints.get(relationship_type)
        if not constraint:
            return
        if constraint.domains and not any(self.is_a(source_type, d) for d in constraint.domains):
            raise ValueError(
                f"Relationship {relationship_type} source type {source_type} violates domain {sorted(constraint.domains)}"
            )
        if constraint.ranges and not any(self.is_a(target_type, r) for r in constraint.ranges):
            raise ValueError(
                f"Relationship {relationship_type} target type {target_type} violates range {sorted(constraint.ranges)}"
            )


def _local_name(uri: URIRef) -> str:
    text = str(uri)
    return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1]

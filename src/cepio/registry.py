from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from rdflib import Graph, OWL, RDF, RDFS, URIRef


class UnknownTypeError(ValueError):
    pass


class AmbiguousTypeError(ValueError):
    pass


@dataclass
class RelationshipConstraint:
    domains: set[str] = field(default_factory=set)
    ranges: set[str] = field(default_factory=set)


@dataclass
class TypeRegistry:
    """IRI-first CEPIO type registry with backwards-compatible aliases.

    Canonical identity is always the full RDF IRI. Local names remain accepted only
    when they resolve unambiguously. This lets CEPIO, source/profile ontologies and
    external standards safely contain identically named types without silently
    collapsing them.
    """

    object_type_ids: set[str] = field(default_factory=set)
    relationship_type_ids: set[str] = field(default_factory=set)
    parents: dict[str, set[str]] = field(default_factory=dict)
    relationship_constraints: dict[str, RelationshipConstraint] = field(default_factory=dict)
    type_aliases: dict[str, set[str]] = field(default_factory=dict)
    relationship_aliases: dict[str, set[str]] = field(default_factory=dict)

    @classmethod
    def from_ontology_dir(cls, ontology_dir: str | Path) -> "TypeRegistry":
        graph = Graph()
        for path in sorted(Path(ontology_dir).glob("*.ttl")):
            graph.parse(path, format="turtle")
        return cls.from_graph(graph)

    @classmethod
    def from_graph(cls, graph: Graph) -> "TypeRegistry":
        registry = cls()
        for subject in graph.subjects(RDF.type, OWL.Class):
            iri = str(subject)
            registry.object_type_ids.add(iri)
            registry._add_alias(registry.type_aliases, _local_name(subject), iri)
            registry._add_alias(registry.type_aliases, _compact_hint(subject), iri)
        for subject, parent in graph.subject_objects(RDFS.subClassOf):
            child_iri, parent_iri = str(subject), str(parent)
            registry.parents.setdefault(child_iri, set()).add(parent_iri)
            registry.object_type_ids.add(child_iri)
            registry.object_type_ids.add(parent_iri)
            registry._add_alias(registry.type_aliases, _local_name(subject), child_iri)
            registry._add_alias(registry.type_aliases, _local_name(parent), parent_iri)
        for subject in graph.subjects(RDF.type, OWL.ObjectProperty):
            iri = str(subject)
            registry.relationship_type_ids.add(iri)
            registry._add_alias(registry.relationship_aliases, _local_name(subject), iri)
            registry._add_alias(registry.relationship_aliases, _compact_hint(subject), iri)
            constraint = registry.relationship_constraints.setdefault(iri, RelationshipConstraint())
            for domain in graph.objects(subject, RDFS.domain):
                constraint.domains.add(str(domain))
            for range_ in graph.objects(subject, RDFS.range):
                constraint.ranges.add(str(range_))
        return registry

    @property
    def object_types(self) -> set[str]:
        return {alias for alias, ids in self.type_aliases.items() if len(ids) == 1 and ":" not in alias}

    @property
    def relationship_types(self) -> set[str]:
        return {alias for alias, ids in self.relationship_aliases.items() if len(ids) == 1 and ":" not in alias}

    def resolve_type(self, value: str) -> str:
        return self._resolve(value, self.object_type_ids, self.type_aliases, "object type")

    def resolve_relationship(self, value: str) -> str:
        return self._resolve(value, self.relationship_type_ids, self.relationship_aliases, "relationship type")

    def aliases_for_type(self, value: str) -> set[str]:
        iri = self.resolve_type(value)
        return {alias for alias, ids in self.type_aliases.items() if iri in ids}

    def is_declared_type(self, type_name: str) -> bool:
        try:
            self.resolve_type(type_name)
            return True
        except (UnknownTypeError, AmbiguousTypeError):
            return False

    def is_declared_relationship(self, relationship_type: str) -> bool:
        try:
            self.resolve_relationship(relationship_type)
            return True
        except (UnknownTypeError, AmbiguousTypeError):
            return False

    def same_type(self, left: str, right: str) -> bool:
        return self.resolve_type(left) == self.resolve_type(right)

    def same_relationship(self, left: str, right: str) -> bool:
        return self.resolve_relationship(left) == self.resolve_relationship(right)

    def is_a(self, type_name: str, expected_type: str) -> bool:
        current_iri = self.resolve_type(type_name)
        expected_iri = self.resolve_type(expected_type)
        if current_iri == expected_iri:
            return True
        seen: set[str] = set()
        stack = [current_iri]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            for parent in self.parents.get(current, set()):
                if parent == expected_iri:
                    return True
                stack.append(parent)
        return False

    def validate_relationship_types(self, relationship_type: str, source_type: str, target_type: str) -> None:
        rel_iri = self.resolve_relationship(relationship_type)
        constraint = self.relationship_constraints.get(rel_iri)
        if not constraint:
            return
        if constraint.domains and not any(self._is_a_iri(self.resolve_type(source_type), d) for d in constraint.domains):
            raise ValueError(f"Relationship {relationship_type} source type {source_type} violates domain {sorted(constraint.domains)}")
        if constraint.ranges and not any(self._is_a_iri(self.resolve_type(target_type), r) for r in constraint.ranges):
            raise ValueError(f"Relationship {relationship_type} target type {target_type} violates range {sorted(constraint.ranges)}")

    def _is_a_iri(self, current_iri: str, expected_iri: str) -> bool:
        if current_iri == expected_iri:
            return True
        seen: set[str] = set()
        stack = [current_iri]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            for parent in self.parents.get(current, set()):
                if parent == expected_iri:
                    return True
                stack.append(parent)
        return False

    @staticmethod
    def _add_alias(target: dict[str, set[str]], alias: str, iri: str) -> None:
        if alias:
            target.setdefault(alias, set()).add(iri)

    @staticmethod
    def _resolve(value: str, canonical_ids: set[str], aliases: dict[str, set[str]], kind: str) -> str:
        if value in canonical_ids:
            return value
        candidates = aliases.get(value, set())
        if not candidates:
            raise UnknownTypeError(f"Unknown CEPIO {kind}: {value}")
        if len(candidates) > 1:
            raise AmbiguousTypeError(
                f"Ambiguous CEPIO {kind} alias '{value}'. Use a namespace-qualified IRI. Candidates: {sorted(candidates)}"
            )
        return next(iter(candidates))


def _local_name(uri: URIRef | str) -> str:
    text = str(uri)
    return text.rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _compact_hint(uri: URIRef | str) -> str:
    text = str(uri)
    local = _local_name(text)
    namespace = text[: -len(local)].rstrip("#/")
    module = namespace.rsplit("/", 1)[-1]
    return f"{module}:{local}" if module else local

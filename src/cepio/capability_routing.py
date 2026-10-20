"""Capability routing and graph projection for CEPIO retrieval."""

from __future__ import annotations

import re

from .capability_registry import CapabilityRecord, CapabilityRegistry
from .retrieval_contracts import (
    CapabilityRoute,
    CapabilityRoutingResult,
    GraphExpansion,
    RetrievalIntent,
)

_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def tokens(value: str) -> set[str]:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return {item.lower() for item in _TOKEN_RE.findall(expanded)}


def term_tail(value: str) -> str:
    return re.split(r"[#/:]", value.rstrip("/#:"))[-1]


class CapabilityRouter:
    """Deterministic reference router over the evidence-backed Capability Registry."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry

    @staticmethod
    def _searchable(capability: CapabilityRecord) -> set[str]:
        values = [
            capability.id,
            capability.title,
            capability.description,
            *capability.semantic_terms,
            *capability.semantic_relationships,
            *capability.personas,
            *capability.competencies,
            *capability.evidence_requirements,
            *capability.reasoning_patterns,
            *capability.skills,
            *capability.decisions,
        ]
        searchable: set[str] = set()
        for value in values:
            searchable.update(tokens(value))
            searchable.update(tokens(term_tail(value)))
        return searchable

    def route(self, intent: RetrievalIntent) -> CapabilityRoutingResult:
        known = {item.id: item for item in self.registry.capabilities}
        unresolved = intent.required_capability_ids - known.keys()
        if unresolved:
            return CapabilityRoutingResult(unresolved_required_capabilities=set(unresolved))

        query_tokens = tokens(intent.query_text)
        query_tokens.update(item.lower() for item in intent.tags)
        routes: list[CapabilityRoute] = []
        for capability in self.registry.capabilities:
            reasons: list[str] = []
            score = 0.0
            if capability.id in intent.capability_hints:
                score = max(score, 1.0)
                reasons.append("explicit capability hint")
            if capability.id in intent.required_capability_ids:
                score = max(score, 1.0)
                reasons.append("required capability")

            if query_tokens:
                searchable = self._searchable(capability)
                overlap = query_tokens & searchable
                if overlap:
                    coverage = len(overlap) / max(1, len(query_tokens))
                    specificity = len(overlap) / max(1, len(searchable))
                    lexical_score = min(0.95, 0.75 * coverage + 0.25 * specificity)
                    score = max(score, lexical_score)
                    reasons.append("matched: " + ", ".join(sorted(overlap)))

            if score > 0.0:
                routes.append(
                    CapabilityRoute(
                        capability_id=capability.id,
                        score=round(score, 6),
                        reasons=reasons,
                    )
                )

        routes.sort(key=lambda item: (-item.score, item.capability_id))
        return CapabilityRoutingResult(routes=routes[: intent.max_capabilities])


class RegistryCapabilityGraph:
    """Reference graph projection derived from reusable capability semantics."""

    def __init__(self, registry: CapabilityRegistry) -> None:
        self.registry = registry
        self._records = {item.id: item for item in registry.capabilities}

    @staticmethod
    def _features(record: CapabilityRecord) -> set[str]:
        return (
            {term_tail(item).lower() for item in record.semantic_terms}
            | {term_tail(item).lower() for item in record.semantic_relationships}
            | {item.lower() for item in record.reasoning_patterns}
            | {item.lower() for item in record.evidence_requirements}
        )

    def expand(
        self,
        capability_ids: set[str],
        *,
        max_results: int,
    ) -> list[GraphExpansion]:
        seeds = [self._records[item] for item in sorted(capability_ids) if item in self._records]
        seed_features = {item.id: self._features(item) for item in seeds}
        expansions: list[GraphExpansion] = []

        for candidate in self.registry.capabilities:
            if candidate.id in capability_ids:
                continue
            candidate_features = self._features(candidate)
            contributing: set[str] = set()
            best = 0.0
            for seed in seeds:
                shared = seed_features[seed.id] & candidate_features
                union = seed_features[seed.id] | candidate_features
                if not shared or not union:
                    continue
                similarity = len(shared) / len(union)
                if similarity > 0.0:
                    contributing.add(seed.id)
                    best = max(best, similarity)
            if best > 0.0:
                expansions.append(
                    GraphExpansion(
                        capability_id=candidate.id,
                        score=round(best, 6),
                        source_capability_ids=contributing,
                    )
                )

        expansions.sort(key=lambda item: (-item.score, item.capability_id))
        return expansions[:max_results]

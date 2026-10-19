"""Deterministic evaluator for CEPIO Enterprise Performance Graph contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .performance_contract import (
    ContributionRelation,
    PerformanceContract,
    PerformanceNode,
    PerformanceStatus,
    PerformanceTarget,
    TargetOperator,
)


_STATUS_SEVERITY: dict[PerformanceStatus, int] = {
    PerformanceStatus.unknown: 0,
    PerformanceStatus.not_evaluated: 0,
    PerformanceStatus.on_track: 1,
    PerformanceStatus.watch: 2,
    PerformanceStatus.at_risk: 3,
    PerformanceStatus.off_track: 4,
    PerformanceStatus.critical: 5,
}


class PerformanceObservation(BaseModel):
    """Evidence-backed value for one performance node."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    value: float
    observed_at: datetime
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    source_subject_id: str | None = None


class PerformanceNodeEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str
    status: PerformanceStatus
    value: float | None = None
    observed_at: datetime | None = None
    evidence_refs: tuple[str, ...] = ()
    source_subject_id: str | None = None
    reasons: tuple[str, ...] = ()
    risk_sources: tuple[str, ...] = ()
    influence_sources: tuple[str, ...] = ()


class PerformanceWorkflowCandidate(BaseModel):
    """Recommendation only; it is not workflow execution authority."""

    model_config = ConfigDict(frozen=True)

    binding_id: str
    source_node_id: str
    source_status: PerformanceStatus
    workflow_definition_id: str
    authority: Literal["recommend_only"] = "recommend_only"
    policy_required: Literal[True] = True
    rationale: str | None = None


class PerformanceEvaluation(BaseModel):
    model_config = ConfigDict(frozen=True)

    contract_id: str
    contract_version: str
    evaluated_at: datetime
    nodes: tuple[PerformanceNodeEvaluation, ...]
    workflow_candidates: tuple[PerformanceWorkflowCandidate, ...] = ()

    def node(self, node_id: str) -> PerformanceNodeEvaluation:
        for evaluation in self.nodes:
            if evaluation.node_id == node_id:
                return evaluation
        raise KeyError(node_id)


class PerformanceRuntime:
    """Evaluate health/change intent without performing any external side effect."""

    def evaluate(
        self,
        contract: PerformanceContract,
        observations: list[PerformanceObservation] | tuple[PerformanceObservation, ...],
        *,
        evaluated_at: datetime | None = None,
    ) -> PerformanceEvaluation:
        now = evaluated_at or datetime.now(timezone.utc)
        if now.tzinfo is None:
            raise ValueError("evaluated_at must be timezone-aware")

        node_map = {node.id: node for node in contract.nodes}
        latest: dict[str, PerformanceObservation] = {}
        for observation in observations:
            if observation.observed_at.tzinfo is None:
                raise ValueError("performance observation timestamps must be timezone-aware")
            if observation.node_id not in node_map:
                raise ValueError(f"observation references unknown node: {observation.node_id}")
            if observation.observed_at > now:
                continue
            current = latest.get(observation.node_id)
            if current is None or observation.observed_at > current.observed_at:
                latest[observation.node_id] = observation

        evaluations: dict[str, PerformanceNodeEvaluation] = {}
        for node in contract.nodes:
            evaluations[node.id] = self._evaluate_node(node, latest.get(node.id), now)

        risk_sources: dict[str, set[str]] = {node.id: set() for node in contract.nodes}
        influence_sources: dict[str, set[str]] = {node.id: set() for node in contract.nodes}

        # Structural graph is acyclic by contract validation. Iterate until the propagated
        # at-risk state reaches a fixed point so multi-hop contribution chains are visible.
        changed = True
        while changed:
            changed = False
            for edge in contract.contributions:
                source = evaluations[edge.source_node_id]
                target = evaluations[edge.target_node_id]

                if edge.relation == ContributionRelation.influences:
                    if _STATUS_SEVERITY[source.status] >= _STATUS_SEVERITY[PerformanceStatus.watch]:
                        if edge.source_node_id not in influence_sources[edge.target_node_id]:
                            influence_sources[edge.target_node_id].add(edge.source_node_id)
                            changed = True
                    continue

                if _STATUS_SEVERITY[source.status] < _STATUS_SEVERITY[PerformanceStatus.watch]:
                    continue

                if edge.source_node_id not in risk_sources[edge.target_node_id]:
                    risk_sources[edge.target_node_id].add(edge.source_node_id)
                    changed = True

                # Do not overwrite a direct target evaluation. An observed node may still
                # expose upstream risk_sources while its current measured result is healthy.
                if target.status in {
                    PerformanceStatus.unknown,
                    PerformanceStatus.not_evaluated,
                } and source.status in {
                    PerformanceStatus.at_risk,
                    PerformanceStatus.off_track,
                    PerformanceStatus.critical,
                }:
                    evaluations[edge.target_node_id] = target.model_copy(
                        update={
                            "status": PerformanceStatus.at_risk,
                            "reasons": target.reasons
                            + (f"At risk via {edge.relation.value} from {edge.source_node_id}",),
                        }
                    )

        for node_id, evaluation in list(evaluations.items()):
            evaluations[node_id] = evaluation.model_copy(
                update={
                    "risk_sources": tuple(sorted(risk_sources[node_id])),
                    "influence_sources": tuple(sorted(influence_sources[node_id])),
                }
            )

        candidates: list[PerformanceWorkflowCandidate] = []
        for binding in contract.response_bindings:
            evaluation = evaluations[binding.node_id]
            if evaluation.status.value in binding.statuses:
                candidates.append(
                    PerformanceWorkflowCandidate(
                        binding_id=binding.id,
                        source_node_id=binding.node_id,
                        source_status=evaluation.status,
                        workflow_definition_id=binding.workflow_definition_id,
                        rationale=binding.rationale,
                    )
                )

        return PerformanceEvaluation(
            contract_id=contract.id,
            contract_version=contract.version,
            evaluated_at=now,
            nodes=tuple(evaluations[node.id] for node in contract.nodes),
            workflow_candidates=tuple(sorted(candidates, key=lambda item: item.binding_id)),
        )

    def _evaluate_node(
        self,
        node: PerformanceNode,
        observation: PerformanceObservation | None,
        now: datetime,
    ) -> PerformanceNodeEvaluation:
        if observation is None:
            return PerformanceNodeEvaluation(
                node_id=node.id,
                status=PerformanceStatus.unknown,
                reasons=("No evidence-backed observation is available",),
            )

        if node.valid_from and observation.observed_at < node.valid_from:
            return PerformanceNodeEvaluation(
                node_id=node.id,
                status=PerformanceStatus.unknown,
                value=observation.value,
                observed_at=observation.observed_at,
                evidence_refs=observation.evidence_refs,
                source_subject_id=observation.source_subject_id,
                reasons=("Observation predates node validity window",),
            )
        if node.valid_to and observation.observed_at >= node.valid_to:
            return PerformanceNodeEvaluation(
                node_id=node.id,
                status=PerformanceStatus.unknown,
                value=observation.value,
                observed_at=observation.observed_at,
                evidence_refs=observation.evidence_refs,
                source_subject_id=observation.source_subject_id,
                reasons=("Observation is outside node validity window",),
            )

        if node.max_observation_age_seconds is not None:
            age = (now - observation.observed_at).total_seconds()
            if age < 0 or age > node.max_observation_age_seconds:
                return PerformanceNodeEvaluation(
                    node_id=node.id,
                    status=PerformanceStatus.unknown,
                    value=observation.value,
                    observed_at=observation.observed_at,
                    evidence_refs=observation.evidence_refs,
                    source_subject_id=observation.source_subject_id,
                    reasons=("Observation is stale for this performance node",),
                )

        if node.target is None and not node.thresholds:
            return PerformanceNodeEvaluation(
                node_id=node.id,
                status=PerformanceStatus.not_evaluated,
                value=observation.value,
                observed_at=observation.observed_at,
                evidence_refs=observation.evidence_refs,
                source_subject_id=observation.source_subject_id,
                reasons=("Observation recorded; node has no evaluable target or threshold",),
            )

        status = PerformanceStatus.on_track
        reasons: list[str] = []

        if node.target is not None:
            if _matches(observation.value, node.target):
                reasons.append("Target met")
            else:
                status = PerformanceStatus.off_track
                reasons.append("Target missed")

        for threshold in node.thresholds:
            if _matches(observation.value, threshold.condition):
                threshold_status = PerformanceStatus(threshold.status)
                if _STATUS_SEVERITY[threshold_status] > _STATUS_SEVERITY[status]:
                    status = threshold_status
                reasons.append(threshold.reason or f"{threshold.status} threshold matched")

        return PerformanceNodeEvaluation(
            node_id=node.id,
            status=status,
            value=observation.value,
            observed_at=observation.observed_at,
            evidence_refs=observation.evidence_refs,
            source_subject_id=observation.source_subject_id,
            reasons=tuple(reasons),
        )


def _matches(value: float, target: PerformanceTarget) -> bool:
    if target.operator == TargetOperator.gte:
        assert target.value is not None
        return value >= target.value
    if target.operator == TargetOperator.lte:
        assert target.value is not None
        return value <= target.value
    if target.operator == TargetOperator.eq:
        assert target.value is not None
        return value == target.value
    assert target.lower_bound is not None
    assert target.upper_bound is not None
    return target.lower_bound <= value <= target.upper_bound

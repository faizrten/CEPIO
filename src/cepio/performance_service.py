"""Headless service boundary for CEPIO Enterprise Performance.

The service composes the durable Performance Contract Registry with the deterministic
Performance Runtime. It exposes resolved contract truth and explainable deviation
assessments without granting workflow execution authority.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .config import RuntimeSettings
from .performance_contract import PerformanceStatus
from .performance_registry import (
    InMemoryPerformanceContractStore,
    PerformanceContractRegistry,
    RegisteredPerformanceContractResolution,
    SQLitePerformanceContractStore,
)
from .performance_runtime import (
    PerformanceEvaluation,
    PerformanceObservation,
    PerformanceRuntime,
    PerformanceWorkflowCandidate,
)


_ACTIONABLE_STATUSES = {
    PerformanceStatus.watch,
    PerformanceStatus.at_risk,
    PerformanceStatus.off_track,
    PerformanceStatus.critical,
}


class PerformanceDeviationAssessment(BaseModel):
    """Explainable deviation extracted from one evaluated performance node."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    status: PerformanceStatus
    value: float | None = None
    observed_at: datetime | None = None
    evidence_refs: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    risk_sources: tuple[str, ...] = ()
    influence_sources: tuple[str, ...] = ()
    workflow_candidates: tuple[PerformanceWorkflowCandidate, ...] = ()


class PerformanceResponseAssessment(BaseModel):
    """Industry-IQ-ready performance assessment; recommendation, never execution."""

    model_config = ConfigDict(frozen=True)

    contract_id: str
    contract_version: str
    organization_id: str | None = None
    evaluated_at: datetime
    source_revision_hashes: tuple[str, ...]
    evaluation: PerformanceEvaluation
    deviations: tuple[PerformanceDeviationAssessment, ...]
    workflow_candidates: tuple[PerformanceWorkflowCandidate, ...]
    authority: str = "recommend_only"
    policy_required: bool = True


class PerformanceService:
    """Protocol-neutral application service for enterprise performance intelligence."""

    def __init__(
        self,
        registry: PerformanceContractRegistry,
        runtime: PerformanceRuntime | None = None,
    ) -> None:
        self.registry = registry
        self.runtime = runtime or PerformanceRuntime()

    def resolve(
        self,
        contract_id: str,
        version: str | None = None,
    ) -> RegisteredPerformanceContractResolution:
        return self.registry.resolve(contract_id, version)

    def evaluate(
        self,
        contract_id: str,
        observations: tuple[PerformanceObservation, ...] | list[PerformanceObservation],
        *,
        version: str | None = None,
        evaluated_at: datetime | None = None,
    ) -> PerformanceResponseAssessment:
        resolution = self.registry.resolve(contract_id, version)
        contract = resolution.resolved.contract
        evaluation = self.runtime.evaluate(
            contract,
            observations,
            evaluated_at=evaluated_at,
        )

        candidates_by_node: dict[str, list[PerformanceWorkflowCandidate]] = {}
        for candidate in evaluation.workflow_candidates:
            candidates_by_node.setdefault(candidate.source_node_id, []).append(candidate)

        deviations = tuple(
            PerformanceDeviationAssessment(
                node_id=node.node_id,
                status=node.status,
                value=node.value,
                observed_at=node.observed_at,
                evidence_refs=node.evidence_refs,
                reasons=node.reasons,
                risk_sources=node.risk_sources,
                influence_sources=node.influence_sources,
                workflow_candidates=tuple(
                    sorted(
                        candidates_by_node.get(node.node_id, ()),
                        key=lambda item: item.binding_id,
                    )
                ),
            )
            for node in evaluation.nodes
            if node.status in _ACTIONABLE_STATUSES
        )

        return PerformanceResponseAssessment(
            contract_id=contract.id,
            contract_version=contract.version,
            organization_id=contract.organization_id,
            evaluated_at=evaluation.evaluated_at,
            source_revision_hashes=tuple(
                revision.definition_hash for revision in resolution.source_revisions
            ),
            evaluation=evaluation,
            deviations=deviations,
            workflow_candidates=evaluation.workflow_candidates,
        )


def build_performance_service(
    settings: RuntimeSettings | None = None,
) -> PerformanceService:
    """Build the reference performance service using the CEPIO persistence setting.

    Development/test ``memory://`` uses an isolated in-memory registry. The reference
    SQLite deployment uses the same database file as the CEPIO runtime but separate
    performance-registry tables.
    """

    resolved_settings = settings or RuntimeSettings.from_env()
    path: Path | None = resolved_settings.sqlite_path()
    store = (
        InMemoryPerformanceContractStore()
        if path is None
        else SQLitePerformanceContractStore(path)
    )
    return PerformanceService(PerformanceContractRegistry(store))

"""Read-only executive envelope over existing governed Performance Industry IQ.

Does not evaluate new formulas or assert causal, contractual or execution authority.
Caller-provided observations are explicitly UNVERIFIED; this is an experimental
preview, not an evidence-binding or production decision endpoint.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from .application_contract import DecisionProposal, ExecutionContext
from .model import ObjectRef
from .performance_contract import PerformanceNodeKind, PerformanceStatus
from .performance_industry_iq import (
    PerformanceIndustryIQService,
    PerformanceReasoningRequest,
)
from .performance_runtime import PerformanceWorkflowCandidate


class ExecutivePackageRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    reasoning: PerformanceReasoningRequest
    financial_node_id: str | None = None
    simulation_only: Literal[True] = True


class ExecutiveAccountability(BaseModel):
    model_config = ConfigDict(frozen=True)

    subject_id: str
    subject_name: str
    subject_kind: str
    relation: str


class ExecutivePerformanceItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    node_id: str
    name: str
    kind: PerformanceNodeKind
    status: PerformanceStatus
    value: float | None = None
    unit: str | None = None
    evidence_refs: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()
    risk_sources: tuple[str, ...] = ()
    influence_sources: tuple[str, ...] = ()
    accountabilities: tuple[ExecutiveAccountability, ...] = ()


class ExecutiveFinancialObservation(BaseModel):
    """An observed currency metric, never an inferred EBITDA or loss estimate."""

    model_config = ConfigDict(frozen=True)

    node_id: str
    name: str
    value: float
    unit: str
    evidence_refs: tuple[str, ...]
    interpretation: Literal["caller_supplied_unverified_currency_metric"] = (
        "caller_supplied_unverified_currency_metric"
    )


class ExecutivePerformancePackage(BaseModel):
    """Protocol-neutral preview for Copilot/Teams/Studio adapters."""

    model_config = ConfigDict(frozen=True)

    contract_id: str
    contract_version: str
    organization_id: str | None = None
    subject: ObjectRef
    focus_node_id: str
    source_revision_hashes: tuple[str, ...]
    performance: tuple[ExecutivePerformanceItem, ...]
    financial_observation: ExecutiveFinancialObservation | None = None
    financial_status: Literal["not_requested", "evidence_missing", "observed_unverified"]
    decision_proposal: DecisionProposal
    workflow_candidates: tuple[PerformanceWorkflowCandidate, ...]
    evidence_status: Literal["caller_supplied_unverified"] = "caller_supplied_unverified"
    authority: Literal["recommend_only"] = "recommend_only"
    policy_required: Literal[True] = True
    decision_persisted: Literal[False] = False
    workflow_started: Literal[False] = False
    action_executed: Literal[False] = False
    causal_claim_made: Literal[False] = False


class ExecutivePerformanceError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class ExecutivePerformanceService:
    """Compose a trusted IQ proposal with existing deterministic Performance state."""

    def __init__(self, iq_service: PerformanceIndustryIQService) -> None:
        self.iq_service = iq_service

    def preview(
        self, request: ExecutivePackageRequest, context: ExecutionContext
    ) -> ExecutivePerformancePackage:
        # This first call owns tenant authorization, source-subject matching,
        # CEPIO object read authorization and contract version pinning.
        iq = self.iq_service.reason(request.reasoning, context)
        performance_service = self.iq_service.performance_service
        resolved = performance_service.resolve(iq.contract_id, iq.contract_version)
        contract = resolved.resolved.contract
        response = performance_service.evaluate(
            iq.contract_id,
            request.reasoning.observations,
            version=iq.contract_version,
            evaluated_at=request.reasoning.evaluated_at,
        )
        # The immutable pinned version is re-evaluated without altering policy.
        if response.source_revision_hashes != iq.source_revision_hashes:
            raise ExecutivePerformanceError(
                "REVISION_CHANGED", "Performance revision changed during preview"
            )
        nodes = {node.id: node for node in contract.nodes}
        subjects = {subject.id: subject for subject in contract.subjects}
        accountabilities: dict[str, list[ExecutiveAccountability]] = {}
        for link in contract.accountabilities:
            subject = subjects[link.subject_id]
            accountabilities.setdefault(link.node_id, []).append(
                ExecutiveAccountability(
                    subject_id=subject.id,
                    subject_name=subject.name,
                    subject_kind=subject.kind.value,
                    relation=link.relation.value,
                )
            )

        items = tuple(
            ExecutivePerformanceItem(
                node_id=item.node_id,
                name=nodes[item.node_id].name,
                kind=nodes[item.node_id].kind,
                status=item.status,
                value=item.value,
                unit=nodes[item.node_id].unit,
                evidence_refs=item.evidence_refs,
                reasons=item.reasons,
                risk_sources=item.risk_sources,
                influence_sources=item.influence_sources,
                accountabilities=tuple(accountabilities.get(item.node_id, ())),
            )
            for item in response.evaluation.nodes
            if nodes[item.node_id].kind
            in {
                PerformanceNodeKind.objective,
                PerformanceNodeKind.key_result,
                PerformanceNodeKind.kpi,
                PerformanceNodeKind.guardrail,
                PerformanceNodeKind.metric,
            }
        )

        financial_observation = None
        financial_status: Literal["not_requested", "evidence_missing", "observed_unverified"] = (
            "not_requested"
        )
        if request.financial_node_id is not None:
            node = nodes.get(request.financial_node_id)
            if (
                node is None
                or node.kind
                not in {
                    PerformanceNodeKind.metric,
                    PerformanceNodeKind.kpi,
                }
                or node.unit not in {"currency", "currency_per_period"}
            ):
                raise ExecutivePerformanceError(
                    "INVALID_FINANCIAL_NODE",
                    "Financial observation must refer to an existing currency KPI or metric",
                )
            item = response.evaluation.node(request.financial_node_id)
            financial_status = "evidence_missing"
            if (
                item.value is not None
                and item.evidence_refs
                and item.status
                not in {
                    PerformanceStatus.unknown,
                    PerformanceStatus.not_evaluated,
                }
            ):
                financial_observation = ExecutiveFinancialObservation(
                    node_id=node.id,
                    name=node.name,
                    value=item.value,
                    unit=node.unit,
                    evidence_refs=item.evidence_refs,
                )
                financial_status = "observed_unverified"

        return ExecutivePerformancePackage(
            contract_id=iq.contract_id,
            contract_version=iq.contract_version,
            organization_id=iq.organization_id,
            subject=iq.subject,
            focus_node_id=iq.node_id,
            source_revision_hashes=iq.source_revision_hashes,
            performance=items,
            financial_observation=financial_observation,
            financial_status=financial_status,
            decision_proposal=iq.decision_proposal,
            workflow_candidates=iq.workflow_candidates,
        )

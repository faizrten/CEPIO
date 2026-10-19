"""Industry IQ reasoning bridge for CEPIO Enterprise Performance.

This module turns an evidence-backed Performance deviation into an explainable Decision
proposal without granting workflow or action execution authority. Performance state is
still evaluated deterministically by :mod:`cepio.performance_runtime`; this layer only
organizes governed context and routes an explicit Decision proposal through the existing
application-service policy boundary.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .application_contract import CEPIOApplicationService, DecisionProposal, ExecutionContext
from .industry_iq import IndustryIQPackManifest
from .model import Decision, ObjectRef
from .performance_contract import PerformanceContract, PerformanceNode
from .performance_runtime import PerformanceObservation, PerformanceWorkflowCandidate
from .performance_service import PerformanceDeviationAssessment, PerformanceResponseAssessment, PerformanceService
from .runtime import CEPIORuntime


PERFORMANCE_RESPONSE_IQ_PACK_ID = "cepio.iq.performance.response"
PERFORMANCE_RESPONSE_DECISION_TYPE = "performance-deviation-response"


class PerformanceReasoningError(ValueError):
    """Fail-closed Performance-to-Decision reasoning error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class PerformanceReasoningRequest(BaseModel):
    """Explicit request to reason about one evaluated performance node."""

    model_config = ConfigDict(frozen=True)

    contract_id: str
    node_id: str
    subject: ObjectRef
    observations: tuple[PerformanceObservation, ...] = Field(min_length=1)
    contract_version: str | None = None
    evaluated_at: datetime | None = None
    context_object_ids: tuple[str, ...] = ()


class PerformanceReasoningAssessment(BaseModel):
    """Explainable, recommend-only Industry IQ output before Decision persistence."""

    model_config = ConfigDict(frozen=True)

    contract_id: str
    contract_version: str
    organization_id: str | None = None
    node_id: str
    node_name: str
    subject: ObjectRef
    deviation: PerformanceDeviationAssessment
    contextual_objects: tuple[ObjectRef, ...] = ()
    workflow_candidates: tuple[PerformanceWorkflowCandidate, ...] = ()
    source_revision_hashes: tuple[str, ...] = ()
    decision_proposal: DecisionProposal
    authority: Literal["recommend_only"] = "recommend_only"
    policy_required: Literal[True] = True
    causal_claim_made: Literal[False] = False


class PerformanceDecisionResult(BaseModel):
    """Governed Decision persisted through CEPIO's existing application boundary."""

    model_config = ConfigDict(frozen=True)

    assessment: PerformanceReasoningAssessment
    decision: Decision
    authority: Literal["recommend_only"] = "recommend_only"
    workflow_started: Literal[False] = False
    action_executed: Literal[False] = False


class PerformanceResponseIndustryIQPack:
    """Deployment capability for governed Performance-deviation Decision proposals."""

    manifest = IndustryIQPackManifest(
        pack_id=PERFORMANCE_RESPONSE_IQ_PACK_ID,
        version="0.1.0",
        requires_core=">=0.4.0,<1.0.0",
        decisions={PERFORMANCE_RESPONSE_DECISION_TYPE},
    )
    pack_id = manifest.pack_id
    version = manifest.version

    def install(self, runtime: CEPIORuntime) -> None:
        runtime.register_decision(
            PERFORMANCE_RESPONSE_DECISION_TYPE,
            allowed_subject_types={"Entity"},
            allowed_actions=set(),
        )


class PerformanceIndustryIQService:
    """Bridge deterministic Performance evidence into a governed CEPIO Decision.

    ``reason`` is side-effect free. ``propose_decision`` persists only a Decision record
    and delegates authorization, creator identity and Decision contract validation to the
    existing :class:`CEPIOApplicationService`. Neither method starts a workflow or
    executes an Action.
    """

    def __init__(
        self,
        performance_service: PerformanceService,
        application_service: CEPIOApplicationService,
    ) -> None:
        self.performance_service = performance_service
        self.application_service = application_service

    def reason(
        self,
        request: PerformanceReasoningRequest,
        context: ExecutionContext,
    ) -> PerformanceReasoningAssessment:
        if not self.application_service.runtime.has_decision(PERFORMANCE_RESPONSE_DECISION_TYPE):
            raise PerformanceReasoningError(
                "PERFORMANCE_IQ_PACK_NOT_INSTALLED",
                "Performance response Industry IQ pack is not installed in the CEPIO runtime",
            )

        resolution = self.performance_service.resolve(
            request.contract_id,
            request.contract_version,
        )
        contract = resolution.resolved.contract
        self._authorize_organization(contract.organization_id, context.tenant_id)

        # Pin the exact authorized revision through evaluation so an active-version change
        # cannot alter the contract after tenant authorization.
        response = self.performance_service.evaluate(
            request.contract_id,
            request.observations,
            version=contract.version,
            evaluated_at=request.evaluated_at,
        )
        deviation = self._deviation(response, request.node_id)
        node = self._node(contract, request.node_id)

        if deviation.source_subject_id is None:
            raise PerformanceReasoningError(
                "SOURCE_SUBJECT_REQUIRED",
                "Only directly evidence-backed deviations with a CEPIO source_subject_id can become Decisions",
            )
        if deviation.source_subject_id != request.subject.id:
            raise PerformanceReasoningError(
                "SOURCE_SUBJECT_MISMATCH",
                f"Performance deviation source subject {deviation.source_subject_id!r} does not match "
                f"requested Decision subject {request.subject.id!r}",
            )

        subject = self.application_service.read_object(request.subject.id, context)
        if subject.type != request.subject.type:
            raise PerformanceReasoningError(
                "SUBJECT_TYPE_MISMATCH",
                f"Decision subject type {request.subject.type!r} does not match CEPIO object type "
                f"{subject.type!r}",
            )

        contextual_objects = self._read_context(request.context_object_ids, context)
        observations = self._decision_observations(
            node,
            deviation,
            contextual_objects,
            contract,
        )
        recommendation = self._recommendation(node, deviation, contract)
        problem = (
            f"How should {subject.name} respond to {node.name} being "
            f"{deviation.status.value} under Performance Contract "
            f"{contract.id}@{contract.version}?"
        )
        proposal = DecisionProposal(
            decision_type=PERFORMANCE_RESPONSE_DECISION_TYPE,
            subject=ObjectRef(id=subject.id, type=subject.type),
            problem=problem,
            observations=observations,
            recommendation=recommendation,
            recommended_action=None,
            confidence=None,
        )

        return PerformanceReasoningAssessment(
            contract_id=contract.id,
            contract_version=contract.version,
            organization_id=contract.organization_id,
            node_id=node.id,
            node_name=node.name,
            subject=proposal.subject,
            deviation=deviation,
            contextual_objects=contextual_objects,
            workflow_candidates=deviation.workflow_candidates,
            source_revision_hashes=response.source_revision_hashes,
            decision_proposal=proposal,
        )

    def propose_decision(
        self,
        request: PerformanceReasoningRequest,
        context: ExecutionContext,
    ) -> PerformanceDecisionResult:
        assessment = self.reason(request, context)
        decision = self.application_service.propose_decision(
            assessment.decision_proposal,
            context,
        )
        return PerformanceDecisionResult(assessment=assessment, decision=decision)

    @staticmethod
    def _authorize_organization(
        organization_id: str | None,
        tenant_id: str | None,
    ) -> None:
        if organization_id is None:
            return
        if tenant_id != organization_id:
            raise PerformanceReasoningError(
                "ORGANIZATION_SCOPE_MISMATCH",
                "Performance Contract is outside the authenticated tenant boundary",
            )

    @staticmethod
    def _deviation(
        response: PerformanceResponseAssessment,
        node_id: str,
    ) -> PerformanceDeviationAssessment:
        for deviation in response.deviations:
            if deviation.node_id == node_id:
                return deviation
        raise PerformanceReasoningError(
            "NODE_NOT_ACTIONABLE",
            f"Performance node {node_id!r} has no actionable deviation in this evaluation",
        )

    @staticmethod
    def _node(contract: PerformanceContract, node_id: str) -> PerformanceNode:
        for node in contract.nodes:
            if node.id == node_id:
                return node
        raise PerformanceReasoningError(
            "NODE_NOT_FOUND",
            f"Performance node {node_id!r} is not present in the resolved contract",
        )

    def _read_context(
        self,
        object_ids: tuple[str, ...],
        context: ExecutionContext,
    ) -> tuple[ObjectRef, ...]:
        refs: list[ObjectRef] = []
        seen: set[str] = set()
        for object_id in object_ids:
            if object_id in seen:
                continue
            seen.add(object_id)
            obj = self.application_service.read_object(object_id, context)
            refs.append(ObjectRef(id=obj.id, type=obj.type))
        return tuple(refs)

    @staticmethod
    def _node_labels(contract: PerformanceContract, node_ids: tuple[str, ...]) -> tuple[str, ...]:
        names = {node.id: node.name for node in contract.nodes}
        return tuple(f"{node_id} ({names.get(node_id, node_id)})" for node_id in node_ids)

    def _decision_observations(
        self,
        node: PerformanceNode,
        deviation: PerformanceDeviationAssessment,
        contextual_objects: tuple[ObjectRef, ...],
        contract: PerformanceContract,
    ) -> list[str]:
        value = "unknown" if deviation.value is None else f"{deviation.value:g}"
        if node.unit:
            value = f"{value} {node.unit}"
        observations = [
            f"{node.name}: status={deviation.status.value}; observed value={value}",
            *(f"Evaluation reason: {reason}" for reason in deviation.reasons),
        ]
        if deviation.evidence_refs:
            observations.append(
                "Performance evidence references: " + ", ".join(deviation.evidence_refs)
            )
        risk_labels = self._node_labels(contract, deviation.risk_sources)
        if risk_labels:
            observations.append("Upstream structural risk sources: " + ", ".join(risk_labels))
        influence_labels = self._node_labels(contract, deviation.influence_sources)
        if influence_labels:
            observations.append(
                "Influence context (not causal proof): " + ", ".join(influence_labels)
            )
        if contextual_objects:
            observations.append(
                "Authorized CEPIO context objects: "
                + ", ".join(f"{item.type}:{item.id}" for item in contextual_objects)
            )
        return observations

    def _recommendation(
        self,
        node: PerformanceNode,
        deviation: PerformanceDeviationAssessment,
        contract: PerformanceContract,
    ) -> str:
        parts = [
            f"Investigate the governed evidence behind the {node.name} deviation before selecting an intervention."
        ]
        risk_labels = self._node_labels(contract, deviation.risk_sources)
        if risk_labels:
            parts.append(
                "Prioritize the upstream structural risk sources in the investigation: "
                + ", ".join(risk_labels)
                + "."
            )
        influence_labels = self._node_labels(contract, deviation.influence_sources)
        if influence_labels:
            parts.append(
                "Review influence context separately and do not treat it as causal proof: "
                + ", ".join(influence_labels)
                + "."
            )
        if deviation.workflow_candidates:
            workflows = ", ".join(
                candidate.workflow_definition_id for candidate in deviation.workflow_candidates
            )
            parts.append(
                "Consider the governed workflow candidate(s) "
                f"{workflows} through Workflow Policy; no workflow has been started."
            )
        else:
            parts.append(
                "No response binding matched this deviation; keep the response recommend-only until a governed workflow or action is selected."
            )
        return " ".join(parts)


PERFORMANCE_RESPONSE_IQ_PACK = PerformanceResponseIndustryIQPack()

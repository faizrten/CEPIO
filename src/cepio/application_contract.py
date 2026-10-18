from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .model import ActionRequest, ActionResult, Decision, ObjectRef, OntologyObject
from .runtime import AuthorizationError, CEPIORuntime
from .skill_preflight import SkillPreflightResult, SkillRegistry


APPLICATION_CONTRACT_VERSION: Literal["0.1.0"] = "0.1.0"


class PrincipalLike(Protocol):
    """Structural identity supplied by a trusted host adapter.

    REST authentication, MCP hosting, SDK embedding, or a workflow host may all provide
    this shape. Application-contract payloads never carry caller-selected identity or
    roles.
    """

    actor_id: str
    roles: set[str]
    tenant_id: str | None


class ExecutionContext(BaseModel):
    """Trusted invocation context injected by the hosting boundary, not user payload."""

    model_config = ConfigDict(frozen=True)

    actor_id: str
    actor_roles: frozenset[str] = Field(default_factory=frozenset)
    tenant_id: str | None = None
    correlation_id: str | None = None

    @classmethod
    def from_principal(
        cls,
        principal: PrincipalLike,
        *,
        correlation_id: str | None = None,
    ) -> ExecutionContext:
        return cls(
            actor_id=principal.actor_id,
            actor_roles=frozenset(principal.roles),
            tenant_id=principal.tenant_id,
            correlation_id=correlation_id,
        )


class ContractMetadata(BaseModel):
    """Protocol-neutral metadata shared by CEPIO application-contract envelopes."""

    model_config = ConfigDict(frozen=True)

    contract_version: Literal["0.1.0"] = APPLICATION_CONTRACT_VERSION
    correlation_id: str | None = None


class EvidenceRole(str, Enum):
    supporting = "supporting"
    contradicting = "contradicting"
    contextual = "contextual"
    assumption = "assumption"


class EvidenceReference(BaseModel):
    """Reference to governed CEPIO evidence without copying the evidence payload."""

    object_ref: ObjectRef
    role: EvidenceRole = EvidenceRole.contextual
    provenance_ref: str | None = None


class ContextEnvelope(BaseModel):
    """Portable industrial context consumed by Skills, applications, and agents."""

    subject: OntologyObject
    related_objects: list[OntologyObject] = Field(default_factory=list)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    assessment_refs: list[ObjectRef] = Field(default_factory=list)
    metadata: ContractMetadata = Field(default_factory=ContractMetadata)


class SkillInvocation(BaseModel):
    """Protocol-neutral request to evaluate one CEPIO Skill.

    Actor identity is deliberately absent. REST/MCP/SDK adapters must inject an
    ``ExecutionContext`` separately at the trusted host boundary.
    """

    skill_id: str
    subject: ObjectRef
    parameters: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    metadata: ContractMetadata = Field(default_factory=ContractMetadata)


class SkillEvaluationStatus(str, Enum):
    completed = "completed"
    blocked = "blocked"
    failed = "failed"


class SkillEvaluation(BaseModel):
    """Stable Skill result independent of REST, MCP, SDK, or provider binding."""

    skill_id: str
    subject: ObjectRef
    status: SkillEvaluationStatus
    recommendation: str | None = None
    outputs: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    assessment_refs: list[ObjectRef] = Field(default_factory=list)
    decision: Decision | None = None
    messages: list[str] = Field(default_factory=list)
    metadata: ContractMetadata = Field(default_factory=ContractMetadata)


class DecisionProposal(BaseModel):
    """Caller-visible Decision proposal; creator identity is host-injected."""

    decision_type: str | None = None
    subject: ObjectRef
    problem: str
    observations: list[str] = Field(default_factory=list)
    recommendation: str
    recommended_action: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ActionIntent(BaseModel):
    """Caller-visible action intent without caller-controlled actor identity."""

    action_type: str
    target: ObjectRef
    parameters: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    correlation_id: str | None = None
    workflow_instance_id: str | None = None
    decision_id: str | None = None


class CEPIOApplicationService:
    """Thin protocol-neutral facade over existing CEPIO runtime semantics.

    This service does not reimplement policy, persistence, decision validation, or
    action execution. It converts stable application-contract requests into existing
    runtime calls while injecting trusted actor context. REST, MCP, SDK and future
    event adapters should converge on this layer instead of duplicating semantics.
    """

    def __init__(
        self,
        runtime: CEPIORuntime,
        *,
        skill_registry: SkillRegistry | None = None,
    ) -> None:
        self.runtime = runtime
        self.skill_registry = skill_registry

    @staticmethod
    def _roles(context: ExecutionContext) -> set[str]:
        return set(context.actor_roles)

    def read_object(self, object_id: str, context: ExecutionContext) -> OntologyObject:
        return self.runtime.read_object_for_actor(object_id, self._roles(context))

    def preflight_skill(
        self,
        skill_id: str,
        context: ExecutionContext,
    ) -> SkillPreflightResult:
        if self.skill_registry is None:
            raise RuntimeError("CEPIO application service has no SkillRegistry configured")
        return self.skill_registry.preflight(
            skill_id,
            actor_id=context.actor_id,
            actor_roles=self._roles(context),
        )

    def propose_decision(
        self,
        proposal: DecisionProposal,
        context: ExecutionContext,
    ) -> Decision:
        roles = self._roles(context)
        if proposal.decision_type and not self.runtime.policy_engine.can_propose_decision(
            roles, proposal.decision_type
        ):
            raise AuthorizationError(
                f"Actor is not authorized to propose decision {proposal.decision_type}"
            )

        self.read_object(proposal.subject.id, context)
        decision = Decision(
            decision_type=proposal.decision_type,
            subject=proposal.subject,
            problem=proposal.problem,
            observations=proposal.observations,
            recommendation=proposal.recommendation,
            recommended_action=proposal.recommended_action,
            confidence=proposal.confidence,
            created_by=context.actor_id,
        )
        return self.runtime.save_decision(decision)

    def get_decision(self, decision_id: str, context: ExecutionContext) -> Decision:
        decision = self.runtime.get_decision(decision_id)
        self.read_object(decision.subject.id, context)
        return decision

    def execute_action(
        self,
        intent: ActionIntent,
        context: ExecutionContext,
    ) -> ActionResult:
        if intent.decision_id is not None:
            self.get_decision(intent.decision_id, context)

        request = ActionRequest(
            action_type=intent.action_type,
            target=intent.target,
            actor_id=context.actor_id,
            actor_roles=self._roles(context),
            parameters=intent.parameters,
            idempotency_key=intent.idempotency_key,
            correlation_id=intent.correlation_id or context.correlation_id,
            workflow_instance_id=intent.workflow_instance_id,
            decision_id=intent.decision_id,
        )
        return self.runtime.execute_action(request)

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .model import ActionRequest, ActionResult, Decision, ObjectRef, OntologyObject
from .runtime import AuthorizationError, CEPIORuntime
from .skill_preflight import SkillPreflightResult, SkillRegistry


APPLICATION_CONTRACT_VERSION: Literal["0.2.0"] = "0.2.0"


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

    contract_version: Literal["0.2.0"] = APPLICATION_CONTRACT_VERSION
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
    assessment_refs: list[ObjectRef] = Field(default_factory=list)
    metadata: ContractMetadata = Field(default_factory=ContractMetadata)


class SkillEvaluationStatus(str, Enum):
    completed = "completed"
    blocked = "blocked"
    failed = "failed"


class DecisionProposal(BaseModel):
    """Caller-visible Decision proposal; creator identity is host-injected."""

    decision_type: str | None = None
    subject: ObjectRef
    problem: str
    observations: list[str] = Field(default_factory=list)
    recommendation: str
    recommended_action: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class SkillExecutionOutput(BaseModel):
    """Internal result returned by one executable Skill procedure.

    The procedure may propose a Decision but does not persist it directly. The
    application service performs that operation with trusted actor context so executable
    Skills cannot choose their own identity or bypass Decision policy.
    """

    recommendation: str | None = None
    outputs: dict[str, Any] = Field(default_factory=dict)
    evidence: list[EvidenceReference] = Field(default_factory=list)
    assessment_refs: list[ObjectRef] = Field(default_factory=list)
    decision_proposal: DecisionProposal | None = None
    messages: list[str] = Field(default_factory=list)


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


class ActionIntent(BaseModel):
    """Caller-visible action intent without caller-controlled actor identity."""

    action_type: str
    target: ObjectRef
    parameters: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    correlation_id: str | None = None
    workflow_instance_id: str | None = None
    decision_id: str | None = None


class SkillExecutionHost:
    """Restricted governed host surface available to executable Skill procedures."""

    def __init__(self, service: CEPIOApplicationService, context: ExecutionContext) -> None:
        self._service = service
        self._context = context

    def read_object(self, object_id: str) -> OntologyObject:
        return self._service.read_object(object_id, self._context)

    def call_function(self, name: str, arguments: dict[str, Any]) -> Any:
        return self._service.call_function(name, arguments, self._context)


class SkillExecutor(Protocol):
    """Executable Skill procedure bound by stable Skill identity."""

    def __call__(
        self,
        invocation: SkillInvocation,
        host: SkillExecutionHost,
    ) -> SkillExecutionOutput: ...


class SkillExecutorRegistry:
    """Host-local registry of executable Skill procedures.

    Admission remains owned by ``SkillRegistry``. This registry only binds a READY Skill
    identity to deterministic executable code and deliberately rejects duplicate
    bindings.
    """

    def __init__(self) -> None:
        self._executors: dict[str, SkillExecutor] = {}

    def register(self, skill_id: str, executor: SkillExecutor) -> None:
        if skill_id in self._executors:
            raise ValueError(f"Executable Skill already registered: {skill_id}")
        self._executors[skill_id] = executor

    def get(self, skill_id: str) -> SkillExecutor:
        try:
            return self._executors[skill_id]
        except KeyError as exc:
            raise KeyError(f"Executable Skill is not bound: {skill_id}") from exc


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
        self.skill_executors = SkillExecutorRegistry()

    def register_skill_executor(self, skill_id: str, executor: SkillExecutor) -> None:
        """Add one executable Skill binding without changing the v0.1 constructor."""

        self.skill_executors.register(skill_id, executor)

    @staticmethod
    def _roles(context: ExecutionContext) -> set[str]:
        return set(context.actor_roles)

    @staticmethod
    def _metadata(invocation: SkillInvocation, context: ExecutionContext) -> ContractMetadata:
        return ContractMetadata(
            correlation_id=invocation.metadata.correlation_id or context.correlation_id
        )

    @staticmethod
    def _merge_evidence(
        original: list[EvidenceReference], added: list[EvidenceReference]
    ) -> list[EvidenceReference]:
        merged: list[EvidenceReference] = []
        seen: set[tuple[str, str, EvidenceRole, str | None]] = set()
        for reference in [*original, *added]:
            key = (
                reference.object_ref.id,
                reference.object_ref.type,
                reference.role,
                reference.provenance_ref,
            )
            if key not in seen:
                seen.add(key)
                merged.append(reference)
        return merged

    @staticmethod
    def _merge_refs(original: list[ObjectRef], added: list[ObjectRef]) -> list[ObjectRef]:
        merged: list[ObjectRef] = []
        seen: set[tuple[str, str]] = set()
        for reference in [*original, *added]:
            key = (reference.id, reference.type)
            if key not in seen:
                seen.add(key)
                merged.append(reference)
        return merged

    def read_object(self, object_id: str, context: ExecutionContext) -> OntologyObject:
        return self.runtime.read_object_for_actor(object_id, self._roles(context))

    def call_function(
        self,
        name: str,
        arguments: dict[str, Any],
        context: ExecutionContext,
    ) -> Any:
        if not self.runtime.policy_engine.can_call_function(self._roles(context), name):
            raise AuthorizationError(f"Actor is not authorized to call function {name}")
        return self.runtime.call_function(name, **arguments)

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

    def evaluate_skill(
        self,
        invocation: SkillInvocation,
        context: ExecutionContext,
    ) -> SkillEvaluation:
        """Preflight and execute one explicitly requested Skill fail-closed.

        v0.2 does not perform trigger matching: the invocation already names the stable
        Skill identity. Every call re-runs actor-aware READY preflight, then invokes only
        an identity-matched executable binding through ``SkillExecutionHost``.
        """

        metadata = self._metadata(invocation, context)
        try:
            preflight = self.preflight_skill(invocation.skill_id, context)
        except KeyError as exc:
            return SkillEvaluation(
                skill_id=invocation.skill_id,
                subject=invocation.subject,
                status=SkillEvaluationStatus.blocked,
                evidence=invocation.evidence,
                assessment_refs=invocation.assessment_refs,
                messages=[f"SKILL_NOT_REGISTERED: {exc}"],
                metadata=metadata,
            )

        if preflight.status != "READY":
            return SkillEvaluation(
                skill_id=invocation.skill_id,
                subject=invocation.subject,
                status=SkillEvaluationStatus.blocked,
                evidence=invocation.evidence,
                assessment_refs=invocation.assessment_refs,
                messages=[f"{check.code}: {check.message}" for check in preflight.blockers],
                metadata=metadata,
            )

        try:
            executor = self.skill_executors.get(invocation.skill_id)
        except KeyError as exc:
            return SkillEvaluation(
                skill_id=invocation.skill_id,
                subject=invocation.subject,
                status=SkillEvaluationStatus.blocked,
                evidence=invocation.evidence,
                assessment_refs=invocation.assessment_refs,
                messages=[f"EXECUTABLE_SKILL_UNBOUND: {exc}"],
                metadata=metadata,
            )

        host = SkillExecutionHost(self, context)
        try:
            output = executor(invocation, host)
        except (AuthorizationError, KeyError, ValueError) as exc:
            return SkillEvaluation(
                skill_id=invocation.skill_id,
                subject=invocation.subject,
                status=SkillEvaluationStatus.failed,
                evidence=invocation.evidence,
                assessment_refs=invocation.assessment_refs,
                messages=[f"SKILL_EXECUTION_FAILED: {exc}"],
                metadata=metadata,
            )

        decision = (
            self.propose_decision(output.decision_proposal, context)
            if output.decision_proposal is not None
            else None
        )
        return SkillEvaluation(
            skill_id=invocation.skill_id,
            subject=invocation.subject,
            status=SkillEvaluationStatus.completed,
            recommendation=output.recommendation,
            outputs=output.outputs,
            evidence=self._merge_evidence(invocation.evidence, output.evidence),
            assessment_refs=self._merge_refs(invocation.assessment_refs, output.assessment_refs),
            decision=decision,
            messages=output.messages,
            metadata=metadata,
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

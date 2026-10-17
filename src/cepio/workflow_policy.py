"""Trusted contextual policy boundary for version-pinned workflow actions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .contextual_policy import (
    PolicyEvaluationContext,
    PolicyObligationKind,
    PolicyRegistry,
    evaluate_policy_set,
)
from .model import ActionRequest, ActionResult, OntologyObject, PolicyDecision, PolicyEffect, utcnow
from .runtime import AuthorizationError

if TYPE_CHECKING:
    from .kinetic import KineticRuntime, WorkflowInstance, WorkflowStepDefinition


class TrustedPolicyContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    subject_id: str
    subject_version: int
    observed_at: datetime = Field(default_factory=utcnow)
    context: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] = Field(default_factory=dict)


class PolicyContextProvider(Protocol):
    def for_action(
        self, request: ActionRequest, target: OntologyObject
    ) -> TrustedPolicyContext: ...


class CanonicalPolicyContextProvider:
    """Use canonical properties, never workflow inputs or action parameters, as context.

    Deployments with derived risk/evidence sources may inject a provider with explicit
    source freshness checks. ``observed_at`` describes the trusted source observation.
    """

    def for_action(self, request: ActionRequest, target: OntologyObject) -> TrustedPolicyContext:
        return TrustedPolicyContext(
            subject_id=target.id,
            subject_version=target.version,
            context=dict(target.properties),
            evidence={"canonical_subject": target.id, "object_version": target.version},
        )


class WorkflowPolicyApprovalPending(Exception):
    def __init__(self, roles: set[str], fingerprint: str):
        super().__init__("Contextual policy requires approval")
        self.roles = roles
        self.fingerprint = fingerprint


class WorkflowPolicyBoundary:
    def __init__(
        self,
        registry: PolicyRegistry,
        provider: PolicyContextProvider | None = None,
        *,
        max_context_age_seconds: float = 60,
    ):
        if max_context_age_seconds < 0:
            raise ValueError("Context age must be nonnegative")
        self.registry = registry
        self.provider = provider or CanonicalPolicyContextProvider()
        self.max_context_age_seconds = max_context_age_seconds

    def execute(
        self,
        kinetic: KineticRuntime,
        instance: WorkflowInstance,
        step: WorkflowStepDefinition,
        request: ActionRequest,
    ) -> ActionResult:
        pending: WorkflowPolicyApprovalPending | None = None

        def guard(
            action: ActionRequest, target: OntologyObject
        ) -> tuple[PolicyDecision, dict[str, Any]]:
            nonlocal pending
            record: dict[str, Any] = {
                "id": str(uuid4()),
                "evaluated_at": utcnow().isoformat(),
                "workflow_instance_id": instance.id,
                "step_id": step.id,
                "policy_references": [
                    r.model_dump(mode="json") for r in instance.policy_references
                ],
            }
            try:
                definition = kinetic._definition(
                    instance.definition_id, instance.definition_version
                )
                if instance.policy_references != definition.policy_references:
                    raise ValueError("Workflow policy pins differ from immutable definition")
                trusted = self.provider.for_action(action, target)
                age = (utcnow() - trusted.observed_at).total_seconds()
                if (
                    trusted.subject_id != target.id
                    or trusted.subject_version != target.version
                    or age < 0
                    or age > self.max_context_age_seconds
                ):
                    raise ValueError("Missing, stale or mismatched trusted policy context")
                context = PolicyEvaluationContext.for_action(
                    action, target, context=trusted.context, evidence=trusted.evidence
                )
                evaluation = evaluate_policy_set(self.registry, instance.policy_references, context)
                record["trusted_context"] = trusted.model_dump(mode="json")
                record["evaluation"] = evaluation.model_dump(mode="json") if evaluation else None
                effect = evaluation.effect if evaluation else PolicyEffect.allow
                reasons = list(evaluation.reasons) if evaluation else []
                roles: set[str] = set()
                if evaluation:
                    for obligation in evaluation.obligations:
                        if obligation.kind == PolicyObligationKind.require_approval_authority:
                            role = obligation.parameters.get("role")
                            if not isinstance(role, str) or not role:
                                raise ValueError("Approval obligation requires an explicit role")
                            roles.add(role)
                        elif obligation.kind == PolicyObligationKind.require_evidence:
                            if not trusted.evidence:
                                raise ValueError("Trusted policy evidence is required")
                        elif obligation.kind == PolicyObligationKind.require_decision_record:
                            if (
                                not action.decision_id
                                or kinetic.runtime.get_decision(action.decision_id) is None
                            ):
                                raise ValueError("Policy requires a persisted Decision record")
                fingerprint = hashlib.sha256(
                    json.dumps(
                        {
                            "evaluation": record["evaluation"],
                            "subject_version": target.version,
                            "parameters": action.parameters,
                            "decision_id": action.decision_id,
                            "context": trusted.context,
                            "evidence": trusted.evidence,
                        },
                        sort_keys=True,
                        default=str,
                    ).encode()
                ).hexdigest()
                record["policy_fingerprint"] = fingerprint
                if effect == PolicyEffect.approval_required or roles:
                    if not roles:
                        raise ValueError("Approval policy requires an explicit approval authority")
                    approval_id = instance.step_states[step.id].policy_approval_id
                    task = kinetic.repository.get_approval(approval_id) if approval_id else None
                    if (
                        task
                        and task.status.value == "approved"
                        and task.decided_by
                        and task.workflow_instance_id == instance.id
                        and task.step_id == step.id
                        and task.policy_fingerprint == fingerprint
                        and task.required_roles == roles
                    ):
                        record["approval_id"] = task.id
                        if effect == PolicyEffect.approval_required:
                            effect = PolicyEffect.allow
                    else:
                        effect = max(
                            (effect, PolicyEffect.approval_required),
                            key=lambda e: {
                                PolicyEffect.allow: 0,
                                PolicyEffect.recommend_only: 1,
                                PolicyEffect.approval_required: 2,
                                PolicyEffect.deny: 3,
                            }[e],
                        )
                        pending = WorkflowPolicyApprovalPending(roles, fingerprint)
                decision = PolicyDecision(effect=effect, reasons=reasons)
            except Exception as exc:
                record["error"] = str(exc)
                decision = PolicyDecision(
                    effect=PolicyEffect.deny, reasons=[f"Workflow policy failed closed: {exc}"]
                )
            kinetic._history(
                instance, "policy_evaluated", action.actor_id, step_id=step.id, details=record
            )
            return decision, record

        try:
            return kinetic.runtime.execute_guarded_action(request, policy_guard=guard)
        except AuthorizationError as exc:
            if (
                pending is not None
                and exc.result is not None
                and exc.result.policy_evidence.get("effective_effect") == "approval_required"
            ):
                raise pending from exc
            raise

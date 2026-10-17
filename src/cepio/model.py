from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Criticality(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    safety_critical = "safety_critical"


class ObjectRef(BaseModel):
    id: str
    type: str


class OntologyObject(BaseModel):
    id: str
    type: str
    name: str
    properties: dict[str, Any] = Field(default_factory=dict)
    interfaces: set[str] = Field(default_factory=set)
    version: int = 1
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class Relationship(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str
    source: ObjectRef
    target: ObjectRef
    properties: dict[str, Any] = Field(default_factory=dict)
    valid_from: datetime | None = None
    valid_to: datetime | None = None


class OperationalEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str
    subject: ObjectRef
    occurred_at: datetime = Field(default_factory=utcnow)
    severity: str | None = None
    properties: dict[str, Any] = Field(default_factory=dict)
    source_system: str | None = None


class Measurement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    subject: ObjectRef
    metric: str
    value: float
    unit: str
    measured_at: datetime = Field(default_factory=utcnow)
    source_system: str | None = None


class KPI(BaseModel):
    id: str
    name: str
    subject: ObjectRef
    value: float
    unit: str
    target: float | None = None
    as_of: datetime = Field(default_factory=utcnow)


class ActionStatus(str, Enum):
    proposed = "proposed"
    authorized = "authorized"
    rejected = "rejected"
    executed = "executed"
    failed = "failed"
    compensated = "compensated"


class PolicyEffect(str, Enum):
    allow = "allow"
    deny = "deny"
    recommend_only = "recommend_only"
    approval_required = "approval_required"


class PolicyDecision(BaseModel):
    effect: PolicyEffect
    reasons: list[str] = Field(default_factory=list)
    allowed_properties: set[str] | None = None
    requires_human_approval: bool = False


class ActionRequest(BaseModel):
    action_type: str
    target: ObjectRef
    actor_id: str
    actor_roles: set[str] = Field(default_factory=set)
    parameters: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = None
    correlation_id: str | None = None
    workflow_instance_id: str | None = None
    decision_id: str | None = None
    requested_at: datetime = Field(default_factory=utcnow)


class ActionResult(BaseModel):
    action_id: str = Field(default_factory=lambda: str(uuid4()))
    action_type: str
    target: ObjectRef
    status: ActionStatus
    message: str
    effects: dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime = Field(default_factory=utcnow)
    audit_id: str | None = None
    replayed: bool = False
    policy_reasons: list[str] = Field(default_factory=list)
    compensation: dict[str, Any] | None = None
    policy_evidence: dict[str, Any] = Field(default_factory=dict)


class AuditEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    action_id: str
    action_type: str
    target: ObjectRef
    actor_id: str
    actor_roles: set[str] = Field(default_factory=set)
    status: ActionStatus
    message: str
    idempotency_key: str | None = None
    correlation_id: str | None = None
    workflow_instance_id: str | None = None
    decision_id: str | None = None
    policy_effect: PolicyEffect | None = None
    policy_reasons: list[str] = Field(default_factory=list)
    effects: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=utcnow)
    replayed: bool = False
    policy_evidence: dict[str, Any] = Field(default_factory=dict)


class Decision(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    decision_type: str | None = None
    subject: ObjectRef
    problem: str
    observations: list[str] = Field(default_factory=list)
    recommendation: str
    recommended_action: str | None = None
    selected_action: str | None = None
    outcome: str | None = None
    confidence: float | None = None
    created_by: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class FunctionInvocation(BaseModel):
    function: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    code: str
    message: str
    request_id: str = Field(alias="requestId")
    details: dict[str, Any] = Field(default_factory=dict)

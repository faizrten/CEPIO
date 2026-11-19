"""IC-2 opt-in task-intent admission BEFORE industrial competence routing.

Candidate-only, read-only and not independently field qualified. The host must
resolve a request-scoped event from its *trusted* session/authorization store.
Do not expose this as a caller-controlled JSON field or an MCP/REST tool.
A passive industrial page and an LLM-inferred purpose never confer authority.
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from enum import Enum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .capability_registry import CapabilityRegistry
from .competence_activation import (
    ActivationHostContext,
    ActivationPolicy,
    ActivationResult,
    ActivationScope,
    ActivationStatus,
    ActivationTask,
    EvidenceAdmission,
    activate_competence_with_host_context,
)

_HEX_64 = re.compile(r"^[0-9a-f]{64}$")


class TaskIntentKind(str, Enum):
    INVESTIGATION = "INVESTIGATION"
    GENERAL_TASK = "GENERAL_TASK"
    DECLINED = "DECLINED"
    UNRESOLVED = "UNRESOLVED"


class TaskIntentOrigin(str, Enum):
    EXPLICIT_USER_INVESTIGATION = "EXPLICIT_USER_INVESTIGATION"
    OTHER_USER_TASK = "OTHER_USER_TASK"
    PASSIVE_CONTEXT = "PASSIVE_CONTEXT"
    MODEL_INFERENCE = "MODEL_INFERENCE"


class HostTaskEvent(BaseModel):
    """Verified *by a host event store*, not by Pydantic or its source fields."""

    model_config = ConfigDict(extra="forbid")
    event_ref: str = Field(min_length=1, max_length=512)
    actor_id: str = Field(min_length=1, max_length=512)
    tenant_id: str = Field(min_length=1, max_length=512)
    session_ref: str = Field(min_length=1, max_length=512)
    request_id: str = Field(min_length=1, max_length=512)
    source_context_ref: str = Field(min_length=1, max_length=512)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    intended_asset_ids: set[str] = Field(default_factory=set)
    intent: TaskIntentKind
    origin: TaskIntentOrigin
    issued_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def validate_event_times(self) -> "HostTaskEvent":
        for value in (self.issued_at, self.expires_at):
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("host task event times must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("task event must have a positive validity interval")
        if not all(
            value.strip()
            for value in (
                self.event_ref,
                self.actor_id,
                self.tenant_id,
                self.session_ref,
                self.request_id,
                self.source_context_ref,
            )
        ):
            raise ValueError("task event identifiers must not be whitespace only")
        return self


class AuthorizedTaskEventResolver(Protocol):
    """Host-implemented session-bound lookup; never an untrusted tool argument."""

    def resolve_authorized(
        self,
        event_ref: str,
        *,
        actor_id: str,
        tenant_id: str,
        session_ref: str,
        request_id: str,
    ) -> HostTaskEvent | None: ...


def _reject(reason: str, *, no_match: bool = False) -> ActivationResult:
    return ActivationResult(
        status=ActivationStatus.NO_MATCH if no_match else ActivationStatus.BLOCKED,
        reason_codes=[reason],
    )


def activate_competence_with_task_admission(
    registry: CapabilityRegistry,
    *,
    task: ActivationTask,
    scope: ActivationScope,
    evidence: list[EvidenceAdmission],
    host_context: ActivationHostContext,
    event_ref: str,
    session_ref: str,
    request_id: str,
    resolver: AuthorizedTaskEventResolver,
    policy: ActivationPolicy | None = None,
) -> ActivationResult:
    """Admit *user-initiated* industrial investigation before routing.

    This source-only contract cannot establish Microsoft Entra validity, user
    gesture provenance, trustworthy source bytes or session-store integrity.
    The host must supply a private, independently authenticated resolver and
    current actor/session/request scope, then independently verify the event.
    """
    if task.asset_id not in scope.permitted_asset_ids or not scope.actor_id:
        return _reject("ASSET_NOT_AUTHORIZED")
    if not isinstance(host_context, ActivationHostContext):
        return _reject("HOST_CONTEXT_NOT_ADMITTED")
    if (
        not isinstance(event_ref, str)
        or not event_ref.strip()
        or not isinstance(session_ref, str)
        or not session_ref.strip()
        or not isinstance(request_id, str)
        or not request_id.strip()
    ):
        return _reject("TASK_INTENT_NOT_VERIFIED")

    # Only the trusted, host-injected store may supply an event. A browser,
    # prompt or LLM passing a matching-looking dictionary is insufficient.
    try:
        event = resolver.resolve_authorized(
            event_ref,
            actor_id=scope.actor_id,
            tenant_id=scope.tenant_id,
            session_ref=session_ref,
            request_id=request_id,
        )
    except Exception:
        return _reject("TASK_INTENT_NOT_VERIFIED")
    if not isinstance(event, HostTaskEvent):
        return _reject("TASK_INTENT_NOT_VERIFIED")

    expected_digest = hashlib.sha256(task.query_text.encode("utf-8")).hexdigest()
    if (
        event.event_ref != event_ref
        or event.actor_id != scope.actor_id
        or event.tenant_id != scope.tenant_id
        or event.session_ref != session_ref
        or event.request_id != request_id
        or event.source_context_ref != host_context.source_ref
        or event.prompt_sha256 != expected_digest
        or not _HEX_64.fullmatch(event.prompt_sha256)
        or not event.issued_at <= task.at < event.expires_at
    ):
        return _reject("TASK_INTENT_NOT_VERIFIED")

    # A task event cannot self-authorize an asset merely because a page contains
    # its industrial context; intended targets come from a user-confirmed
    # workflow control and must be reconciled against the actual asset crosswalk.
    if event.intended_asset_ids and event.intended_asset_ids != {task.asset_id}:
        return _reject("ASSET_INTENT_CONFLICT")
    if event.intent in {TaskIntentKind.GENERAL_TASK, TaskIntentKind.DECLINED}:
        return _reject("TASK_NOT_AN_INVESTIGATION", no_match=True)
    if event.intent != TaskIntentKind.INVESTIGATION:
        return _reject("TASK_INTENT_NOT_VERIFIED")
    if (
        event.origin != TaskIntentOrigin.EXPLICIT_USER_INVESTIGATION
        or event.intended_asset_ids != {task.asset_id}
    ):
        return _reject("TASK_INTENT_NOT_VERIFIED")

    return activate_competence_with_host_context(
        registry,
        task=task,
        scope=scope,
        evidence=evidence,
        host_context=host_context,
        policy=policy,
    )

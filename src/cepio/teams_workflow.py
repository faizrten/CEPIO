from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

from .adapters import (
    AdapterVerificationStatus,
    GovernedVerificationRequest,
    GovernedVerificationResult,
    GovernedWriteReceipt,
    GovernedWriteRequest,
)
from .model import utcnow


TEAMS_WORKFLOW_SYSTEM = "microsoft_teams_workflow"
TEAMS_ATTENTION_OPERATION = "post_attention_card"
TEAMS_ATTENTION_SCHEMA_VERSION: Literal["0.1"] = "0.1"


class TeamsAttentionSeverity(str, Enum):
    info = "info"
    warning = "warning"
    high = "high"
    critical = "critical"


class TeamsAttentionEvent(BaseModel):
    """Provider-neutral attention event projected into a Microsoft Teams card."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    summary: str
    severity: TeamsAttentionSeverity = TeamsAttentionSeverity.info
    subject_id: str
    subject_type: str
    subject_label: str | None = None
    recommendation: str | None = None
    impact: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    context_url: str | None = None
    occurred_at: datetime = Field(default_factory=utcnow)

    @field_validator("context_url")
    @classmethod
    def validate_context_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("Teams attention context_url must be an absolute HTTPS URL")
        return value


class TeamsWorkflowEnvelope(BaseModel):
    schema_version: Literal["0.1"] = TEAMS_ATTENTION_SCHEMA_VERSION
    event: TeamsAttentionEvent
    adaptive_card: dict[str, Any]


@dataclass(frozen=True)
class TeamsWebhookResponse:
    status_code: int
    request_id: str | None = None


TeamsWebhookTransport = Callable[
    [str, dict[str, Any], dict[str, str], float], TeamsWebhookResponse
]


def _severity_label(severity: TeamsAttentionSeverity) -> str:
    return {
        TeamsAttentionSeverity.info: "Information",
        TeamsAttentionSeverity.warning: "Warning",
        TeamsAttentionSeverity.high: "High",
        TeamsAttentionSeverity.critical: "Critical",
    }[severity]


def build_teams_adaptive_card(event: TeamsAttentionEvent) -> dict[str, Any]:
    facts = [
        {"title": "Severity", "value": _severity_label(event.severity)},
        {
            "title": "Subject",
            "value": event.subject_label or f"{event.subject_type} · {event.subject_id}",
        },
    ]
    if event.confidence is not None:
        facts.append({"title": "Confidence", "value": f"{event.confidence:.0%}"})
    if event.impact:
        facts.append({"title": "Impact", "value": event.impact})

    body: list[dict[str, Any]] = [
        {
            "type": "TextBlock",
            "text": "CEPIO Industry IQ",
            "weight": "Bolder",
            "size": "Small",
            "isSubtle": True,
        },
        {
            "type": "TextBlock",
            "text": event.title,
            "weight": "Bolder",
            "size": "Large",
            "wrap": True,
        },
        {"type": "FactSet", "facts": facts},
        {"type": "TextBlock", "text": event.summary, "wrap": True},
    ]

    if event.recommendation:
        body.extend(
            [
                {
                    "type": "TextBlock",
                    "text": "Recommended action",
                    "weight": "Bolder",
                    "spacing": "Medium",
                },
                {
                    "type": "TextBlock",
                    "text": event.recommendation,
                    "wrap": True,
                },
            ]
        )

    if event.evidence:
        body.extend(
            [
                {
                    "type": "TextBlock",
                    "text": "Evidence",
                    "weight": "Bolder",
                    "spacing": "Medium",
                },
                {
                    "type": "TextBlock",
                    "text": "\n".join(f"• {item}" for item in event.evidence),
                    "wrap": True,
                },
            ]
        )

    actions: list[dict[str, Any]] = []
    if event.context_url:
        actions.append(
            {
                "type": "Action.OpenUrl",
                "title": "Open in Industry IQ Studio",
                "url": event.context_url,
            }
        )

    card: dict[str, Any] = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": body,
    }
    if actions:
        card["actions"] = actions
    return card


def build_teams_attention_payload(event: TeamsAttentionEvent) -> dict[str, Any]:
    return TeamsWorkflowEnvelope(
        event=event,
        adaptive_card=build_teams_adaptive_card(event),
    ).model_dump(mode="json")


def _validate_webhook_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("Teams Workflow webhook URL must be an absolute HTTPS URL")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Teams Workflow webhook URL must not contain userinfo or a fragment")
    return value


def _post_json(
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout_seconds: float,
) -> TeamsWebhookResponse:
    request = Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            status = int(getattr(response, "status", response.getcode()))
            request_id = (
                response.headers.get("x-ms-workflow-run-id")
                or response.headers.get("x-ms-request-id")
                or response.headers.get("request-id")
            )
    except HTTPError as exc:
        raise RuntimeError(
            f"Teams Workflow webhook rejected the request with HTTP {exc.code}"
        ) from exc
    except URLError as exc:
        raise RuntimeError("Teams Workflow webhook transport failed") from exc

    if status < 200 or status >= 300:
        raise RuntimeError(f"Teams Workflow webhook returned HTTP {status}")
    return TeamsWebhookResponse(status_code=status, request_id=request_id)


class TeamsWorkflowWebhookAdapter:
    """Governed outbound binding to a Teams Workflows webhook trigger.

    The webhook URL is runtime configuration and is never included in CEPIO receipts,
    source payloads, cards, or error messages. HTTP acceptance proves only transport
    acknowledgement; end-to-end card delivery remains unverified until a callback or
    Teams agent integration is introduced.
    """

    system_name = TEAMS_WORKFLOW_SYSTEM

    def __init__(
        self,
        webhook_url: str,
        *,
        timeout_seconds: float = 10.0,
        transport: TeamsWebhookTransport | None = None,
    ) -> None:
        self._webhook_url = _validate_webhook_url(webhook_url)
        self._timeout_seconds = timeout_seconds
        self._transport = transport or _post_json
        self._receipts: dict[str, GovernedWriteReceipt] = {}

    def write_governed(self, request: GovernedWriteRequest) -> GovernedWriteReceipt:
        if request.system != self.system_name:
            raise ValueError(
                f"Teams adapter cannot handle system {request.system!r}; expected {self.system_name!r}"
            )
        if request.operation != TEAMS_ATTENTION_OPERATION:
            raise ValueError(
                f"Teams adapter does not support operation {request.operation!r}"
            )

        prior = self._receipts.get(request.idempotency_key)
        if prior is not None:
            return prior.model_copy(deep=True)

        envelope = TeamsWorkflowEnvelope.model_validate(request.payload)
        outbound = envelope.model_dump(mode="json")
        outbound["cepio"] = {
            "execution_id": request.execution_id,
            "action_id": request.action_id,
            "decision_id": request.decision_id,
            "canonical_object_id": request.canonical_object_id,
            "destination": request.external_id,
            "idempotency_key": request.idempotency_key,
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "CEPIO-Teams-Workflow/0.1",
            "X-CEPIO-Idempotency-Key": request.idempotency_key,
        }
        response = self._transport(
            self._webhook_url,
            outbound,
            headers,
            self._timeout_seconds,
        )
        receipt = GovernedWriteReceipt(
            accepted=True,
            source_request_id=response.request_id
            or f"TEAMS-{uuid4().hex[:12].upper()}",
            message="Teams Workflow webhook accepted the attention event",
            source_payload={
                "http_status": response.status_code,
                "delivery_verification": "transport_acknowledged",
            },
        )
        self._receipts[request.idempotency_key] = receipt.model_copy(deep=True)
        return receipt

    def verify_write(
        self, request: GovernedVerificationRequest
    ) -> GovernedVerificationResult:
        if request.idempotency_key not in self._receipts:
            return GovernedVerificationResult(
                status=AdapterVerificationStatus.not_applied,
                message="No Teams Workflow transport receipt exists for this idempotency key",
            )
        return GovernedVerificationResult(
            status=AdapterVerificationStatus.unknown,
            message=(
                "Teams Workflow transport was acknowledged, but end-to-end Teams card "
                "delivery is not yet verifiable in v0.1"
            ),
            source_payload={"source_request_id": request.source_request_id},
        )

    def reconcile_write(
        self, request: GovernedVerificationRequest
    ) -> GovernedVerificationResult:
        return self.verify_write(request)

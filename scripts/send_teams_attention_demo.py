from __future__ import annotations

import os
import sys
from uuid import uuid4

from cepio.adapters import GovernedWriteRequest
from cepio.teams_workflow import (
    TEAMS_ATTENTION_OPERATION,
    TEAMS_WORKFLOW_SYSTEM,
    TeamsAttentionEvent,
    TeamsAttentionSeverity,
    TeamsWorkflowWebhookAdapter,
    build_teams_attention_payload,
)


def main() -> int:
    webhook_url = os.getenv("CEPIO_TEAMS_WORKFLOW_URL", "").strip()
    if not webhook_url:
        print(
            "CEPIO_TEAMS_WORKFLOW_URL is required. Configure a Teams Workflow with "
            "the 'When a Teams webhook request is received' trigger, then set its URL "
            "only in the local process environment.",
            file=sys.stderr,
        )
        return 2

    event = TeamsAttentionEvent(
        title="Rig 07 NPT risk needs attention",
        summary=(
            "CEPIO detected a rising non-productive-time risk signal during the "
            "current drilling interval."
        ),
        severity=TeamsAttentionSeverity.high,
        subject_id="rig-07",
        subject_type="DrillingRig",
        subject_label="Rig 07",
        recommendation="Review the NPT evidence and initiate the approved diagnostic workflow.",
        impact="Potential schedule and invisible-lost-time exposure",
        confidence=0.86,
        evidence=[
            "Synthetic drilling event stream: repeated connection delay pattern",
            "NPT assessment: elevated operational deviation",
            "CEPIO policy: recommendation only; no external operational action executed",
        ],
    )
    idempotency_key = f"teams-demo:{uuid4()}"
    request = GovernedWriteRequest(
        execution_id=f"demo-{uuid4()}",
        system=TEAMS_WORKFLOW_SYSTEM,
        operation=TEAMS_ATTENTION_OPERATION,
        external_id="teams-demo-destination",
        canonical_object_id="rig-07",
        action_id=f"demo-action-{uuid4()}",
        actor_id="cepio-demo",
        idempotency_key=idempotency_key,
        payload=build_teams_attention_payload(event),
    )

    adapter = TeamsWorkflowWebhookAdapter(webhook_url)
    receipt = adapter.write_governed(request)
    print("Teams Workflow accepted CEPIO attention event")
    print(f"request_id={receipt.source_request_id}")
    print(f"http_status={receipt.source_payload.get('http_status')}")
    print("delivery_verification=transport_acknowledged (human delivery not yet verified)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

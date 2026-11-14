# Microsoft Teams Action Surface v0.1

## Purpose

Use Microsoft Teams as CEPIO's first lightweight human attention surface while Industry IQ Studio evolves from observation into governed write/operate experiences.

v0.1 deliberately supports **outbound attention cards only**. It proves that CEPIO can project governed industrial context into Teams without making Teams authoritative for industrial semantics, policy, identity, or execution.

```text
CEPIO decision / action context
          |
          v
TeamsAttentionEvent
          |
          v
Adaptive Card projection
          |
          v
Teams Workflow webhook
          |
          v
Microsoft Teams
```

## Boundary

Teams is an interaction surface. CEPIO remains authoritative for:

- industrial objects and relationships;
- evidence and provenance;
- Skills and Decisions;
- actor authority and policy;
- governed Actions;
- verification and audit.

The Teams Workflow webhook URL is runtime configuration and MUST NOT be committed to source control, emitted in logs, copied into cards, stored in audit payloads, or exposed to model-callable tool arguments.

## v0.1 contract

`TeamsAttentionEvent` carries:

- title and summary;
- severity;
- canonical subject identity/type;
- optional recommendation;
- optional impact;
- optional confidence;
- compact evidence statements;
- optional HTTPS deep link to Industry IQ Studio.

CEPIO projects the event into Adaptive Card v1.5 and keeps an **internal**
`TeamsWorkflowEnvelope` containing `schema_version`, `event`, and
`adaptive_card`. That envelope is a CEPIO governed Action payload, **not**
the HTTP body accepted by the Teams Workflow webhook.

The adapter sends Microsoft's documented *Teams webhook trigger* schema:

```json
{
  "type": "message",
  "attachments": [
    {
      "contentType": "application/vnd.microsoft.card.adaptive",
      "contentUrl": null,
      "content": {
        "type": "AdaptiveCard",
        "version": "1.5",
        "body": [{ "type": "TextBlock", "text": "CEPIO Industry IQ" }]
      }
    }
  ]
}
```

The adapter carries CEPIO idempotency in the outbound `X-CEPIO-Idempotency-Key`
header and retains execution/action metadata in CEPIO governed runtime records;
it does not send internal actor, destination, or policy metadata as unsupported
top-level webhook fields. Teams is never an authoritative action ledger.

The Power Automate flow should use the webhook body's first attachment
`content` (the Adaptive Card), **not** a hypothetical top-level
`adaptive_card` property. For the single-card CEPIO v0.1 payload, the
expression is `first(triggerBody()?['attachments'])?['content']`.

## Governed adapter

`TeamsWorkflowWebhookAdapter` implements CEPIO's existing `GovernedWriteAdapter` contract:

```text
system    = microsoft_teams_workflow
operation = post_attention_card
```

The adapter:

- validates HTTPS-only webhook configuration;
- preserves CEPIO idempotency metadata;
- sends the card as JSON;
- never returns or logs the webhook URL;
- records only non-secret transport metadata in the receipt;
- treats HTTP success as **transport acknowledgement only**.

### Verification semantics

Teams Workflow v0.1 cannot prove that the card was rendered or read by a human. Therefore:

```text
HTTP accepted        -> adapter receipt accepted
end-to-end delivery  -> UNKNOWN
human acknowledgement -> NOT IMPLEMENTED in v0.1
```

This is intentional. CEPIO must not convert an HTTP 200/202 into false operational certainty.

A future callback/Teams-agent binding can promote delivery/response to a verifiable external outcome.

## Quick proof

1. In Teams Workflows (or Power Automate), create a new workflow with the
   **When a Teams webhook request is received** trigger. For the local,
   synthetic-data-only proof, select the appropriate unauthenticated webhook
   option so the script can POST without a delegated Entra token; treat the
   generated webhook URL as a bearer secret. Never use an unrestricted public
   endpoint for real operational or customer-sensitive data.
2. Add Microsoft Teams **Post card in a chat or channel**, choosing a
   test channel/chat you control. In its Adaptive Card field use the Power Automate
   expression `first(triggerBody()?['attachments'])?['content']`.
   CEPIO v0.1 deliberately sends one card per request.
3. Save the workflow, then copy its generated HTTPS webhook URL. Ensure the
   Teams Workflows app/connector is allowed in the tenant.
4. In a local shell, set the URL as a process-only secret:

```powershell
$env:CEPIO_TEAMS_WORKFLOW_URL = '<workflow webhook URL>'
python scripts/send_teams_attention_demo.py
```

Confirm both a successful workflow run and the rendered card in Teams; an HTTP 200/202 alone only acknowledges transport. The demo sends a synthetic Rig 07 NPT attention event. It does not invoke SAP, PI, Fabric, or any customer system.

After testing:

```powershell
Remove-Item Env:CEPIO_TEAMS_WORKFLOW_URL
```

## Production integration pattern

The demo script is only a transport proof. Production attention delivery should be registered behind CEPIO's `ExternalActionRuntime` so an outbound notification originates from an already-authorized CEPIO Action and inherits immutable audit/idempotency behavior.

Example binding shape:

```python
from cepio.external_actions import ExternalActionBinding
from cepio.teams_workflow import (
    TEAMS_ATTENTION_OPERATION,
    TEAMS_WORKFLOW_SYSTEM,
    TeamsWorkflowWebhookAdapter,
)

external.register_adapter(TeamsWorkflowWebhookAdapter(webhook_url))
external.register_binding(
    ExternalActionBinding(
        action_type="NotifyTeamsAttention",
        system=TEAMS_WORKFLOW_SYSTEM,
        operation=TEAMS_ATTENTION_OPERATION,
        payload_builder=my_attention_payload_builder,
    )
)
```

The target's `ExternalIdentityMapping.external_id` should be a non-secret destination alias such as `rig-operations-channel`; it must not contain the webhook URL.

## Next decision gate

After the first real card is proven, choose between:

### v0.2 Workflow response callback

Use a Teams/Power Automate Adaptive Card response to call a dedicated authenticated CEPIO endpoint. Suitable for a small command set such as:

- acknowledge;
- investigate;
- approve/reject;
- escalate.

The callback must map the Teams identity to a CEPIO actor and re-run CEPIO authority/policy checks before any command is accepted.

### Teams agent / MCP

Use the hosted CEPIO `/mcp` surface for conversational interaction where users ask follow-up questions, inspect evidence, compare alternatives, and invoke governed CEPIO tools.

The likely end state is:

```text
Teams Workflow -> proactive attention / cards
Teams Agent    -> conversational Industry IQ via MCP
Studio         -> deep investigation, configuration, simulation and governance
```

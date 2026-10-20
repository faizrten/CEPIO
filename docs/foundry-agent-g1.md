# Foundry Agent Lighthouse — G1 Runbook

Issue: #248  
Parent program: #246

## Goal

Qualify one real Microsoft Foundry-hosted agent against CEPIO's governed MCP surface:

```text
Foundry Agent
    ↓ agentic identity
CEPIO remote MCP
    ↓ actor-aware admission
CEPIO executable Skill
    ↓ governed evidence
CEPIO Decision
```

G1 is **recommendation/Decision only**. External action execution is intentionally outside this gate.

A repository merge makes the proof path available. It does **not** constitute a live Foundry PASS. A PASS requires a real Foundry response artifact that satisfies the G1 qualifier.

## 1. Install

For the remote MCP host:

```bash
pip install -e '.[mcp]'
```

For the live Foundry caller:

```bash
pip install -e '.[foundry-live]'
```

## 2. Configure the CEPIO MCP host

Use normal CEPIO runtime/auth settings plus the MCP-specific settings below.

```bash
export CEPIO_ENVIRONMENT=production
export CEPIO_DB_URL='sqlite:////home/data/cepio.db'

export CEPIO_AUTH_MODE=entra
export CEPIO_ENTRA_TENANT_ID='<tenant-id>'
export CEPIO_ENTRA_AUDIENCE='api://<cepio-mcp-app-registration>'

# Explicit external Entra application-role → CEPIO-role mapping.
export CEPIO_MCP_ENTRA_ROLE_MAP='{"CEPIO.Agent.Recommender":"ai_agent_recommender"}'

# Required by the MCP Streamable HTTP transport's DNS-rebinding protection.
export CEPIO_MCP_ALLOWED_HOSTS='cepio-mcp.example.com,cepio-mcp.example.com:*'

# G1 deliberately does not publish cepio_execute_action.
export CEPIO_MCP_TOOL_PROFILE='recommendation-only'

# The host is loopback-only by default. Set this explicitly only when the
# deployment ingress/container must accept external connections.
export CEPIO_MCP_BIND_HOST='0.0.0.0'
```

Start the remote MCP service:

```bash
cepio-foundry-mcp
```

The endpoint is:

```text
https://<cepio-mcp-host>/mcp
```

`CEPIO_MCP_BIND_HOST` defaults to `127.0.0.1`. Production platform configuration must deliberately opt into a broader bind address when the ingress model requires it; external exposure must still be protected by TLS, Entra authentication, and the MCP host/origin allowlists.

The hosting layer validates the bearer token with CEPIO's existing Entra token validator, maps only configured Entra roles/groups into CEPIO roles, and binds the result through `ContextVarActorProvider`. Tool arguments cannot supply actor identity or roles.

### G1 least-privilege tool surface

The `recommendation-only` profile exposes seven tools:

- `cepio_get_object`
- `cepio_query_objects`
- `cepio_get_state_at`
- `cepio_explain_property`
- `cepio_call_function`
- `cepio_evaluate_skill`
- `cepio_recommend_action`

It does **not** expose `cepio_execute_action`.

CEPIO policy remains authoritative even when a host uses the narrower profile.

## 3. Create the Foundry remote MCP connection

Set the active Foundry project:

```bash
export FOUNDRY_PROJECT_ENDPOINT='https://<account>.services.ai.azure.com/api/projects/<project>'
azd ai project set "$FOUNDRY_PROJECT_ENDPOINT"
```

Create the connection with agent identity:

```bash
azd ai connection create cepio-mcp-g1 \
  --kind remote-tool \
  --target https://<cepio-mcp-host>/mcp \
  --auth-type agentic-identity \
  --audience 'api://<cepio-mcp-app-registration>'
```

For G1, publish the Foundry agent before final qualification so the agent receives its own identity rather than relying on the pre-publication shared project identity. Assign that identity only the CEPIO Entra application role required for recommendation, for example `CEPIO.Agent.Recommender`.

Configure the agent to use the `cepio-mcp-g1` remote MCP connection. Do not attach direct Fabric SQL, SAP write, CEPIO database, or repository tools to the G1 agent.

## 4. Prepare a synthetic/reference CEPIO scenario

The live CEPIO runtime must contain the subject, evidence and any parameters required by the executable Skill under test.

The public application host currently ships an executable maintenance-deferral reference Skill:

```text
cepio.skill.maintenance.assess-maintenance-deferral
```

The repository also qualifies the equipment-degradation Skill contract at admission/preflight level. Detailed differentiated Reliability IQ and protected evaluation content belong in CEPIO-Labs rather than this public runbook.

G1 can be run with any executable Skill that satisfies #248. Set the exact required Skill ID in the runner so a different Skill cannot accidentally satisfy qualification.

## 5. Run the Foundry agent

Set:

```bash
export CEPIO_FOUNDRY_PROJECT_ENDPOINT="$FOUNDRY_PROJECT_ENDPOINT"
export CEPIO_FOUNDRY_AGENT_NAME='<published-agent-name>'
export CEPIO_FOUNDRY_G1_SKILL_ID='cepio.skill.maintenance.assess-maintenance-deferral'
export CEPIO_FOUNDRY_G1_PROMPT='<scenario-specific prompt instructing the agent to use CEPIO only, evaluate the required Skill, create the governed Decision, cite/use CEPIO evidence, and never execute an external Action>'
```

Run:

```bash
python scripts/qualify_foundry_agent_g1.py
```

Optional report location:

```bash
export CEPIO_FOUNDRY_G1_REPORT=/secure/path/foundry-g1-qualification.json
```

The report contains the raw Foundry response. Treat it as potentially sensitive and do not commit a customer run artifact.

## 6. Qualification rule

The qualifier does not grade the model's prose. It inspects Foundry Responses API protocol evidence.

PASS requires:

- at least one actual MCP call to `cepio_evaluate_skill`;
- the requested Skill ID, when configured, appears in the invocation;
- the Skill output is `completed`;
- the Skill output carries at least one governed evidence reference;
- a persisted CEPIO Decision ID is present;
- **no** `cepio_execute_action` MCP call occurred.

A model statement such as "I evaluated the Skill" without an MCP call cannot pass.

## 7. G1 claim boundary

Passing this gate proves:

- a real Foundry agent can operate through CEPIO MCP;
- Microsoft/Entra identity can be translated into CEPIO authority without model-supplied roles;
- CEPIO executable Skills can return evidence-backed governed Decisions;
- external Action execution can be excluded from the agent's exposed surface.

It does not yet prove:

- proactive Fabric event activation (G3);
- Teams/Copilot approval (G4);
- SAP writeback or external Outcome verification (G5);
- final protected Reliability benchmark qualification (G6);
- Cognite portability (G7).

## Microsoft references

- Prompt agent quickstart: https://learn.microsoft.com/azure/foundry/agents/quickstarts/prompt-agent
- MCP authentication: https://learn.microsoft.com/azure/foundry/agents/how-to/mcp-authentication
- Tool authentication: https://learn.microsoft.com/azure/foundry/agents/how-to/tools/tool-authentication
- MCP tools: https://learn.microsoft.com/azure/foundry/agents/how-to/tools/model-context-protocol

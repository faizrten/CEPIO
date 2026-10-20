# Microsoft Foundry Reliability G1 Qualification

## Purpose

G1 is the first live proof of the CEPIO Microsoft-native industrial-agency boundary:

> **Microsoft owns agent execution. CEPIO owns industrial agency.**

The proof uses a real Microsoft Foundry prompt agent and the existing CEPIO remote MCP endpoint. The agent may inspect governed CEPIO context and evaluate the qualified Reliability Skill, but it cannot reach CEPIO action tools at all.

```text
Foundry Agent Service
        |
        | Remote MCP / agent identity
        v
CEPIO MCP endpoint
        |
        +-- get/query/state/provenance
        +-- deterministic Functions
        +-- evaluate Reliability Skill
        |
        X-- recommend action (not exposed)
        X-- execute action   (not exposed)
        |
        v
CEPIO Decision
```

This is intentionally narrower than the later lighthouse gates. G1 proves hosted agency, governed evidence, Skill execution and Decision persistence. It does **not** prove proactive triggering, human approval UX or source-system writeback.

## Preconditions

1. A Microsoft Foundry project using the current Agent Service API.
2. A deployed chat-capable model.
3. A reachable CEPIO MCP endpoint hosted with verified Microsoft Entra authentication.
4. A Foundry `RemoteTool` project connection targeting that endpoint. Use agent identity for the production proof.
5. The CEPIO host has the protected Reliability Skill `cepio.skill.reliability.investigate-equipment-degradation` admitted, executable and READY for the mapped agent role.
6. Synthetic or approved non-customer evidence for the G1 compressor is available through CEPIO.

The public CEPIO repository intentionally does not publish the differentiated Reliability Skill implementation or protected evaluation corpus. CEPIO-Labs owns that qualification material.

## Foundry connection

Create the remote MCP connection using the current Azure Developer CLI/Foundry tooling:

```bash
azd ai project set "$FOUNDRY_PROJECT_ENDPOINT"

azd ai connection create "$CEPIO_MCP_CONNECTION_NAME" \
  --kind remote-tool \
  --target "$CEPIO_MCP_SERVER_URL" \
  --auth-type agentic-identity \
  --audience "$CEPIO_MCP_AUDIENCE"
```

The connection authenticates the Foundry agent to the MCP endpoint. CEPIO still maps the verified Entra identity into CEPIO roles and independently evaluates authorization on every operation.

## Install the live proof dependencies

Keep the Foundry client dependencies outside the CEPIO package itself:

```bash
pip install -e .
pip install 'azure-ai-projects>=2.3,<3' 'azure-identity>=1.20,<2' 'openai>=3,<4'
```

The proof uses the stable Microsoft Foundry Projects SDK (`azure-ai-projects>=2.3`) and Entra authentication through `DefaultAzureCredential`. These are host/qualification dependencies, not CEPIO runtime dependencies.

## Environment

Required:

```text
FOUNDRY_PROJECT_ENDPOINT
FOUNDRY_MODEL_DEPLOYMENT_NAME
CEPIO_MCP_SERVER_URL
CEPIO_MCP_CONNECTION_NAME
```

Optional:

```text
CEPIO_FOUNDRY_AGENT_NAME   default: cepio-reliability-g1
CEPIO_G1_SUBJECT_ID        default: K-101
```

## Run

```bash
python scripts/run_foundry_reliability_g1.py
```

The runner creates a temporary server-side Foundry prompt-agent version, gives it only the G1 allow-listed CEPIO MCP tools, invokes the equipment-degradation investigation, records the complete Foundry response as qualification evidence and deletes the temporary agent version.

### G1 tool allow-list

```text
cepio_get_object
cepio_query_objects
cepio_get_state_at
cepio_explain_property
cepio_call_function
cepio_evaluate_skill
```

### Hard exclusions

```text
cepio_recommend_action
cepio_execute_action
```

The exclusion is implemented in the Foundry MCP tool definition through `allowed_tools`. It is therefore a host-level capability restriction, not merely a prompt instruction.

## Qualification conditions

The runner returns `PASS` only when the Foundry response contains:

- a `cepio_evaluate_skill` call;
- the exact Reliability Skill identity;
- no use of either prohibited action tool;
- no blocked/failed Skill status.

The protected CEPIO-Labs qualification adds the stronger industrial assertions:

- Skill is READY for the authenticated agent role;
- required current-run evidence is present;
- the Skill produces an evidence-backed CEPIO Decision;
- unsupported or fabricated evidence fails closed;
- no action/audit side effect is produced;
- the same protected scenario remains deterministic under the reference/conformance host.

## Identity boundary

The model must never provide `actor_id` or CEPIO roles in tool arguments. The CEPIO MCP hosting layer validates the Microsoft Entra token and maps verified claims through `EntraClaimsMapper` / `ContextVarActorProvider` before the gateway runs.

For G1, use a least-privilege agent role that can:

- read the required Reliability context;
- call the required deterministic Reliability Functions;
- evaluate the Reliability Skill;
- propose the required Decision;

but cannot execute an external Action.

## Failure conditions

G1 fails if any of the following occurs:

1. the Foundry agent requires direct Fabric SQL, SAP, repository or runtime access;
2. CEPIO-specific roles are accepted from model/tool arguments;
3. the Reliability Skill is not READY;
4. the agent answers materially without current-run CEPIO evidence;
5. the Skill does not persist the governed Decision expected by the protected qualification;
6. an action/recommend-action tool appears in the agent's G1 tool surface;
7. Foundry-specific concepts require changes to canonical CEPIO semantics.

## Relationship to later gates

G1 deliberately stops at Decision creation.

```text
G1  Foundry -> CEPIO evidence/Skill -> Decision
G2  add Industrial Mandate
G3  add proactive Fabric/Microsoft trigger
G4  add Teams/Copilot human approval UX
G5  add SAP governed Action -> verify -> Outcome
G6  qualify through protected industrial evals
G7  repeat the same capability over Cognite evidence
```

Do not pull G3-G5 behavior into G1 merely to make the demo appear more autonomous. The program is intentionally progressive and fail-closed.

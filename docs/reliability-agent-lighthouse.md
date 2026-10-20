# Microsoft-native Reliability Agent Lighthouse

**Program issue:** #246  
**Architecture decision:** ADR-0032  
**Classification:** PUBLIC execution contract; protected Industry IQ/evaluation internals remain in CEPIO-Labs.

## Mission

Prove one end-to-end industrial agent loop using Microsoft-hosted agency and CEPIO-owned industrial operating intelligence:

```text
Event / request
    ↓
Microsoft Foundry / Copilot
    ↓
CEPIO MCP
    ↓
Capability routing
    ↓
Reliability Industry IQ + Skill
    ↓
Governed evidence
    ↓
CEPIO Decision
    ↓
Policy / Authority
    ↓
Human approval UX where required
    ↓
CEPIO governed SAP Action
    ↓
verify / reconcile
    ↓
WorkflowOutcome
```

The lighthouse is successful only if CEPIO remains the industrial operating contract rather than becoming the generic agent host.

## Execution sequence

### G0 — Architecture alignment

Deliverables:
- ADR-0032 accepted;
- #246 becomes the program spine;
- #59, #58, #67, #53, #57 and #2 explicitly align to the lighthouse rather than spawning parallel runtimes;
- generic agent-host responsibilities are removed from the CEPIO critical path unless demanded by a concrete industrial gap.

Exit:
- one documented Microsoft/CEPIO ownership boundary;
- no new general-purpose CEPIO agent-framework epic.

### G1 — Real Foundry Agent → CEPIO MCP

Use existing assets:
- `src/cepio/integrations/microsoft/foundry_mcp.py`;
- `src/cepio/integrations/microsoft/foundry_gateway.py`;
- Foundry MCP registration/deployment artifacts;
- Entra actor identity boundary;
- Skill preflight/READY dispatch;
- Reliability Industry IQ capability.

First scenario:

> Investigate degradation of compressor K-101 and produce an evidence-backed recommendation. Do not execute an external action.

Required path:

```text
Foundry agent
   ↓ CEPIO MCP only
resolve K-101
   ↓
retrieve authorized evidence
   ↓
activate Reliability capability
   ↓
Skill READY preflight
   ↓
evaluate Skill
   ↓
persist Decision
```

Acceptance:
- agent has no direct CEPIO runtime dependency;
- agent has no direct Fabric/SAP write access;
- all material claims cite current-run CEPIO evidence;
- Skill is READY for authenticated actor/context;
- Decision is persisted through governed CEPIO application/runtime path;
- no external Action is executed;
- Foundry trace can be correlated to CEPIO invocation/Decision identity where available.

### G2 — Industrial Mandate Contract

Implement only after G1 demonstrates the need.

The mandate should compose existing contracts:

```text
Performance Contract  → why / objective
Capability Contract   → what CEPIO may do
Skill                  → how
Evidence Contract      → with what evidence
Policy / Authority     → under what authority
Decision / Outcome     → completion semantics
```

Minimum fields:
- mandate ID/version;
- objective;
- subject reference;
- permitted capability IDs/version constraints;
- evidence requirements;
- authority ceiling (`observe`, `recommend`, `approve`, `execute`);
- completion criteria;
- escalation conditions;
- validity/expiry;
- expected Outcome type.

Non-goals:
- conversation/session state;
- model planning state;
- general task graph;
- LLM prompt ownership.

### G3 — Proactive trigger

Preferred Microsoft-native path:

```text
Fabric / RTI / Operations signal
        ↓
Microsoft trigger infrastructure
        ↓
Industrial Mandate / CEPIO capability invocation
        ↓
Foundry/Copilot agent
```

CEPIO owns the semantic meaning of the condition and the allowed industrial response, not the generic trigger scheduler.

Acceptance:
- same G1 capability can start from an event rather than a human prompt;
- trigger transport/provider details remain outside CEPIO Core;
- duplicate/replayed event does not duplicate industrial side effects;
- event provenance is retained in CEPIO evidence/Decision lineage.

### G4 — Human governance through Microsoft UX

Flow:

```text
CEPIO Decision
      ↓
approval requirement
      ↓
Copilot Studio / Teams UX
      ↓
human response
      ↓
CEPIO revalidates identity + authority + policy + preconditions
```

Acceptance:
- Microsoft gathers approval; CEPIO decides whether approval is sufficient;
- mismatch/expired/unauthorized approval fails closed;
- approval evidence is linked to Decision/Action lineage;
- no UI approval bypass can invoke the underlying provider write directly.

### G5 — Closed-loop SAP action

Reuse:
- #53 SAP provider;
- #57 external identity/write/verify/reconcile;
- #67 durable Action/verification/Outcome runtime.

First action target:
- create inspection or maintenance notification/work order for the lighthouse compressor.

Required path:

```text
Decision
  ↓
valid approval
  ↓
CEPIO Action
  ↓
SAP provider
  ↓
SAP result
  ↓
read-back verification
  ↓
reconciliation
  ↓
WorkflowOutcome
```

Acceptance:
- source-authoritative object/transaction ID recorded;
- idempotent action semantics qualified;
- unknown outcomes reconcile rather than blind-retry;
- external result is verified rather than inferred from transport success;
- complete actor → Decision → approval → Action → provider call/result → Outcome audit lineage exists.

### G6 — Industrial assurance

Protected qualification in CEPIO-Labs.

Required scenario families:
- normal degradation with sufficient evidence;
- missing required evidence;
- contradictory evidence;
- wrong actor authority;
- prohibited direct action attempt;
- provider/tool failure;
- approval expiry/mismatch;
- duplicated trigger/action request;
- verified external success;
- ambiguous/unknown external outcome.

Measure where practical:

```text
raw model
vs + evidence
vs + semantics
vs + Industry IQ
vs + governance
```

Autonomy must not expand beyond the level qualified by the scenario/evaluation gate.

### G7 — Cognite portability proof

Freeze the logical subject from G1/G6 and replace only the evidence-source binding:

```text
Fabric-backed evidence
        ↓ replace
Cognite-backed evidence
```

Acceptance:
- same Industrial Mandate;
- same CEPIO Capability IDs;
- same Skill package/version;
- same Decision schema;
- same authority/action semantics;
- no CEPIO Core changes;
- provider-specific provenance differs as expected;
- no duplicated authoritative industrial graph required solely for CEPIO execution.

## Critical-path ownership

| Work | Existing owner |
|---|---|
| Program/lighthouse | #246 + #59 |
| Compressor reference scenario | #58 |
| Foundry MCP / Microsoft binding | existing Microsoft integration surface |
| Provenance/lineage | #2 |
| SAP source action | #53 |
| External identity/write/verify/reconcile | #57 |
| Industrial workflow/approval/action/outcome | #67 |
| Protected scenario/eval qualification | CEPIO-Labs |
| Cognite provider portability proof | new bounded binding experiment |

## Stop-doing rules

Do not add the following to the critical path unless the lighthouse exposes a concrete missing industrial requirement:

- general-purpose agent runtime;
- model router;
- conversation/session framework;
- generic event scheduler;
- multi-agent bus;
- generic approval product;
- generic RAG/search/vector infrastructure;
- broad source-adapter framework work disconnected from the lighthouse;
- ontology expansion for coverage without qualification evidence.

## Program exit claim

After G1–G6 pass, CEPIO may claim:

> A Microsoft-hosted AI agent can use qualified CEPIO Industry IQ to investigate an industrial condition over governed enterprise evidence, persist an auditable industrial Decision, respect CEPIO authority, obtain required human authorization through Microsoft work experiences, execute a governed source-of-record Action and verify the resulting Outcome.

G7 adds the stronger portability claim that the same industrial agency contract is independent of the Microsoft data plane.

# ADR-0032 — Microsoft-native industrial agency boundary

**Status:** Proposed  
**Date:** 2026-10-20  
**Classification:** PUBLIC architecture contract

## Context

CEPIO is pursuing a new North Star:

> **CEPIO is the portable industrial operating intelligence layer for Energy & Process Industries: thin in infrastructure, thick in industrial intelligence.**

CEPIO already contains substantial agent-adjacent runtime capability: governed MCP tools, Industry IQ Packs, Skills, capability routing, evidence/provenance, Decisions, policy/authority, durable workflows, governed Actions, verification/reconciliation and Outcomes.

Because CEPIO is Microsoft-native, Microsoft Foundry, Copilot Studio, Microsoft 365 Copilot/Teams, Entra and Fabric should provide the generic agent-host and work-experience capabilities rather than CEPIO rebuilding a competing general-purpose agent framework.

The architectural question is therefore not whether CEPIO becomes agentic in isolation. It is which parts of industrial agency CEPIO must own so that Microsoft-hosted agents can operate safely, portably and with durable industrial meaning.

## Decision

Adopt the following product boundary:

> **Microsoft owns agent execution. CEPIO owns industrial agency.**

### Microsoft-owned responsibilities

Microsoft platform services may provide:

- frontier-model hosting and invocation;
- general planning and tool-loop mechanics;
- conversation and session UX;
- event/trigger infrastructure;
- generic business-process flows;
- Teams / Microsoft 365 Copilot interaction;
- human approval UX;
- model and agent tracing/observability;
- generic connector/runtime infrastructure.

CEPIO must not create competing infrastructure for these concerns unless a concrete industrial requirement cannot be satisfied through an existing platform boundary.

### CEPIO-owned responsibilities

CEPIO owns the portable industrial operating contract:

- industrial identity and semantics;
- industrial state and time;
- evidence and provenance requirements;
- capability and Industry IQ contracts;
- Skill admission and READY-only dispatch;
- industrial Decisions;
- industrial authority and policy;
- governed industrial Actions;
- source-result verification/reconciliation semantics;
- Outcomes and audit lineage;
- industrial assurance, scenarios and qualification criteria.

### Agent-host relationship

Production Microsoft deployments should prefer:

```text
Microsoft Foundry / Copilot-hosted agent
              ↓
          CEPIO MCP
              ↓
       CEPIO Industry IQ
              ↓
 evidence · Decision · authority · Action · Outcome
```

The existing `ConstrainedOperatorAgent` remains valuable as a **reference/conformance agent**, not as the required production agent host.

### Industrial Mandate

CEPIO may introduce a small compositional **Industrial Mandate Contract** to express the industrial operating boundary supplied to an agent. It should reuse existing contracts rather than duplicate model/session/planning abstractions.

Minimum mandate semantics:

- objective;
- subject;
- permitted capabilities;
- required evidence;
- authority ceiling;
- completion criteria;
- escalation conditions;
- expiry/validity;
- required Outcome semantics.

The mandate should compose existing Performance, Capability, Skill, Evidence, Policy/Authority and Decision/Outcome contracts where possible.

## Consequences

### Positive

- CEPIO remains thin in infrastructure while thickening Industry IQ.
- Foundry/Copilot can evolve independently from CEPIO canonical semantics.
- Microsoft-native deployment is accelerated by existing CEPIO MCP and Entra boundaries.
- CEPIO retains portability to Cognite and future agent hosts.
- Existing workflow/action investment remains useful for industrial governance without becoming a generic workflow platform.
- Scenario Lab and Industrial Evals become the assurance layer for Microsoft-hosted industrial agents.

### Constraints

CEPIO should not build, by default:

- a general-purpose agent framework;
- a proprietary model router or LLM gateway;
- a conversation/session platform;
- a generic event scheduler;
- a multi-agent messaging bus;
- generic approval UX;
- a proprietary vector/search platform;
- a generic RAG framework.

Infrastructure work must be justified by a missing industrial operating requirement, not by feature parity with agent platforms.

## Reference lighthouse

Issue #246 is the primary proof program:

```text
Fabric / industrial event
        ↓
Microsoft Foundry / Copilot
        ↓
CEPIO MCP
        ↓
Reliability Industry IQ + Skill
        ↓
Evidence-backed CEPIO Decision
        ↓
CEPIO authority / policy
        ↓
Teams/Copilot approval UX where required
        ↓
CEPIO governed SAP Action
        ↓
verify / reconcile
        ↓
WorkflowOutcome
```

The lighthouse must preserve:

- no direct agent-to-source write bypass;
- no unsupported material claims;
- complete material-evidence traceability;
- explicit authority ceiling;
- source-authoritative verification;
- replayable assurance qualification;
- no model/vendor-specific concepts in CEPIO Core.

## Portability requirement

Microsoft-native does not mean Microsoft-dependent.

The same CEPIO Capability / Skill / Decision / Policy contract should later operate over a Cognite-backed evidence provider without CEPIO Core or Skill changes. Provider-specific identifiers and provenance remain in platform bindings.

## IP boundary

This ADR is public because the architecture boundary improves interoperability and ecosystem adoption.

Protected assets remain outside the public architecture surface, including detailed Industry IQ logic, industrial heuristics, proprietary evaluation corpora, benchmark scenarios and promotion evidence. Customer-specific mappings, thresholds, procedures, identities and operational data remain customer-confidential.

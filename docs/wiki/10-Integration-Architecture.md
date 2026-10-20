# Integration Architecture

## Integration principle

CEPIO does not replace systems of record, systems of observation or industrial data platforms. It binds authoritative enterprise context through a stable operating contract.

> **Reuse -> Bind -> Extend -> Own only where CEPIO adds reusable industrial operating intelligence.**

```text
Authoritative source/platform
 SAP · PI · OSDU · P6 · MES · engineering · Fabric · Cognite
       |
       v
provider-specific reader / transport
       |
       v
CEPIO Binding Contract
       |
       v
canonical identity + evidence + state + provenance
       |
       v
Industry IQ / Skill / Decision / Performance
       |
       v
policy / authority / governed Action
       |
       v
source execution -> read-back -> verify -> reconcile -> Outcome
```

## Binding Contract

The current source-neutral integration boundary is the CEPIO Binding Contract rather than a monolithic generic connector platform.

A provider binding should preserve:

- stable CEPIO identity;
- canonical type/property/relationship mapping;
- evidence references and source lineage;
- event/observation time;
- provider-specific transport separation from domain semantics;
- authenticated/authorized Action handoff;
- external acknowledgement/read-back;
- verification and reconciliation;
- deterministic/fail-closed error handling.

Provider-specific transport belongs outside CEPIO Core semantics.

## Integration ownership

```text
Source/platform owns:
- authoritative raw facts/transactions
- provider transport/API semantics
- provider-native lifecycle

CEPIO owns:
- canonical industrial identity/meaning
- evidence/provenance contract
- cross-source operational state
- Skill/Decision/authority semantics
- governed Action intent
- verification/reconciliation/Outcome meaning
```

## SAP S/4HANA / EAM

Intended authoritative roles include:

- equipment / functional-location context;
- maintenance notifications/work orders;
- maintenance history;
- materials/spares where required;
- procurement/vendor context where required;
- governed work-order/writeback execution target.

Current mainline contains generic external identity/write/verify/reconcile foundations, but the **live SAP product qualification remains open** under v0.5 CONNECT.

The CONNECT proof requires more than a fake/reference write contract: it needs real source acknowledgement/read-back, idempotency, reconciliation and failure/observability evidence.

## AVEVA PI / historian

Authoritative roles include:

- time-series observations;
- equipment/process state signals;
- events/anomalies;
- event-time evidence for Functions, Skills and Decisions.

The historian remains authoritative for raw measurements. CEPIO adds asset meaning, operational context, evidence/provenance and decision relevance.

A real PI/historian qualification remains a v0.5 CONNECT P0 proof.

## OSDU / upstream

OSDU should remain an authoritative upstream/subsurface data foundation rather than being recreated inside CEPIO.

Recommended boundary:

```text
OSDU / ADME authoritative technical records
       |
       v
CEPIO binding / identity / evidence
       |
       v
uncertainty · Opportunity · Decision · authority · workflow · Action · Outcome
```

CEPIO should reuse/bind strong upstream objects such as Well, Wellbore, trajectories, seismic, logs, interpretations, grids and reservoir models while owning cross-domain operating meaning that OSDU does not attempt to define.

The OSDU-first boundary and domain runtime bindings are already on main; full live operational adapter qualification remains separate.

## Primavera P6

Potential authoritative roles include:

- project schedules;
- turnaround planning;
- EPCIC activities;
- dependencies and milestones.

P6 remains a valid third-domain path for CONNECT/reference applications but is not yet a qualified live product baseline.

## Fabric / OneLake / Fabric IQ

Fabric can provide enterprise data/operational context beneath CEPIO.

Current mainline includes:

- Fabric/Fabric IQ semantic binding contracts;
- provider-neutral Binding Contract usage;
- Fabric live-proof transport path;
- secretless/OIDC deployment foundations.

The transport/provider is Microsoft-specific; industrial semantics and Industry IQ must remain provider-neutral.

A strategic portability test is that the same competency/Skill/Decision contract can operate over Fabric or another provider without changing CEPIO Core.

## Cognite and other industrial platforms

Cognite Data Fusion or another industrial data platform should be treated as an alternative authoritative context provider, not a competing semantic truth that CEPIO must copy wholesale.

The goal is:

```text
Fabric evidence ----+
                    |
Cognite evidence ---+--> same CEPIO competency / Skill / Decision contract
                    |
OSDU evidence ------+
```

Provider-specific bindings may differ; the CEPIO industrial operating contract should remain stable.

## Azure AI Search

Azure AI Search is **not** an authoritative industrial integration source. It is an optional physical retrieval projection behind CEPIO Retrieval & Indexing.

Rules:

- Capability Registry / MemoryStore remain authoritative;
- Search results are tenant/expiry revalidated;
- raw SAP/PI/customer data is not automatically duplicated into Search;
- Search ranking does not grant authority or satisfy evidence requirements by itself.

## External Action lifecycle

Current mainline external execution foundation follows:

```text
CEPIO Decision / Action intent
 -> policy + authority
 -> canonical-to-source identity resolution
 -> idempotent source execution
 -> acknowledgement/read-back
 -> verification
 -> reconciliation
 -> WorkflowOutcome / audit
```

Ambiguous source identity fails closed. Unknown write state must be reconciled rather than treated as success.

## Integration maturity model

### Level 0 — static mapping

Source extracts map into CEPIO with explicit semantics.

### Level 1 — refreshable evidence

Mappings refresh with stable identity and provenance.

### Level 2 — event-driven operational state

Near-real-time source events update or inform CEPIO state/evidence.

### Level 3 — governed external Action

CEPIO executes an authorized external Action through the Binding/Action boundary.

### Level 4 — verified closed loop

The source result is read back, verified and reconciled into CEPIO Outcome/audit.

### Level 5 — portable capability

The same CEPIO competency/Skill/Decision behavior works across multiple provider bindings without Core semantic change.

## Current release boundary

v0.5 CONNECT is not qualified until one industrial asset combines meaningful context from at least three authoritative source domains and completes one authenticated, idempotent, verified and reconciled writeback.

See [Current State](../current-state.md), [Binding Contract](../developer/platform-bindings.md), [External Action Runtime](../external-action-runtime.md) and [Roadmap](17-Roadmap.md).

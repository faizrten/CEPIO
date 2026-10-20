# Temporal State, Evidence and Provenance

## Why time matters

Industrial data is rarely just "current" or "historical". Corrections, late-arriving events, backdated facts, model outputs and delayed source acknowledgements mean at least two different questions must remain distinguishable:

1. What was true in the industrial world at time T?
2. What did CEPIO know at time T?

CEPIO therefore uses **bitemporal semantics** and explicit evidence/provenance lineage.

## Valid time

Valid time describes when a fact is true in the domain.

Example:

```text
Compressor operatingState = tripped
valid from 10:02 to 10:18
```

## Transaction time

Transaction time describes when CEPIO stored or learned a fact.

A late-arriving event may have:

```text
occurred_at       10:02
recorded_by_CEPIO 10:07
```

Both are meaningful.

## Object and relationship history

CEPIO can reconstruct prior object/relationship views under valid-time and transaction-time semantics.

Conceptually:

```python
runtime.get_object_at("K-201", transaction_time)
runtime.get_object_valid_at("K-201", valid_time)
```

Temporal relationships matter when equipment moves, suppliers/contracts change, people/authority assignments change, work is reassigned or asset ownership changes.

This allows historical graph structure itself to be reconstructed rather than projecting today's relationships backward in time.

## Event-to-state projection

Events are immutable occurrences. Derived state can be replayed deterministically.

```text
Immutable events
     |
     v
Deterministic projector
     |
     v
Derived state
```

Benefits include:

- reproducibility;
- explainability;
- debugging;
- recovery;
- replay after projector logic changes;
- causal lineage from source occurrence into operational state.

Derived/rebuildable state must never mutate the source event history used to reproduce it.

## Property provenance

CEPIO can record provenance at property/state level.

An explanation may include:

```text
property: asset:criticality
value: A
source_system: SAP
source_entity: Equipment
source_field: ABCINDIC
source_record: 10001234
mapping_version: sap-eam-v3
transformation_run: run-2026-10-14-001
observed_time: ...
ingestion_time: ...
source_value_hash: ...
```

The exact source fields vary by binding/provider; CEPIO's provenance meaning should remain stable.

## Evidence vs model output

Evidence is not the same as a model-generated explanation.

```text
Source record / observation / document / validated calculation
        -> Evidence / SourceReference
        -> governed reasoning
        -> model or Function output
```

A plausible model statement does not create source evidence.

```text
Model Output != Evidence
```

Agent/Skill reasoning should cite or consume evidence that is authorized and available in the current execution context.

## Decision lineage

Decision intelligence should preserve the evidence and temporal context that existed when the Decision was made.

```text
Evidence + State + Time + Uncertainty
             |
             v
       Skill / Function
             |
             v
          Decision
```

A later correction to source data should not erase what the actor legitimately knew at Decision time. Transaction-time history makes that distinction auditable.

## Action and Outcome lineage

External execution adds another causal chain:

```text
Decision
 -> Action
 -> Action audit
 -> provider binding / source request
 -> acknowledgement
 -> verification / reconciliation
 -> WorkflowOutcome
```

A source acknowledgement is not automatically proof of the intended industrial Outcome. Verification/reconciliation must retain the causal link to the originating Decision/Action.

Unknown write state remains explicitly unknown until authoritative source truth is reconciled.

## Workflow policy lineage

Durable workflow instances can pin exact policy versions and retain trusted evaluation context so later audit can answer:

- which policy version governed the step;
- which actor/authority was evaluated;
- which evidence/context supported approval/denial;
- which Action and external effect followed.

This is important when policy itself evolves after the workflow starts.

## Memory and retrieval provenance

CEPIO Memory, Retrieval & Indexing and Compiled Industry IQ add additional projection layers, but they do not replace source provenance.

- durable memory should retain evidence/source references;
- retrieval returns candidates, not new facts;
- search indexes are rebuildable projections;
- compiled capability bundles are deterministic projections of governed capability records;
- cache/index lineage cannot grant authority or satisfy missing source evidence by itself.

```text
Index != Source of Truth
Cache != Authority
```

## Performance lineage

Performance Contracts can connect KPI/KR/guardrail evaluation to underlying industrial evidence and downstream Decisions/workflows.

Reference performance semantics should preserve which formula/target/scope specialization was active when a value or deviation was evaluated rather than treating KPI meaning as timeless/universal.

## Operational lineage vs enterprise catalogue lineage

CEPIO provenance is runtime/decision/action oriented.

Enterprise catalog systems such as Purview may receive or supply governance/lineage context, but catalog lineage does not replace CEPIO's operational provenance model.

## Explainability for humans and AI

A trustworthy explanation can distinguish:

```text
What is true?
What evidence supports it?
Where did that evidence come from?
When was it valid?
When did CEPIO know it?
Which transformation/mapping produced the derived value?
Which Decision used it?
Which Action followed?
Was the source effect verified?
What Outcome was observed?
```

That is materially safer than grounding an industrial answer in an untraceable flattened dataset or model narrative.

## Current product boundary

Temporal/provenance foundations are strong on main, but the v0.5 CONNECT release still requires live multi-source provenance plus a real verified/reconciled external writeback in the K-201 lighthouse.

See [Integration Architecture](10-Integration-Architecture.md), [Functions/Decisions/Actions](08-Functions-Decisions-Actions.md), [Current State](../current-state.md) and [Roadmap](17-Roadmap.md).

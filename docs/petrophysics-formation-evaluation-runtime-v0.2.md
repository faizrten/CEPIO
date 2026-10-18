# CEPIO Petrophysics — PET-02 Runtime Execution v0.2

## Purpose

PET-02 v0.2 turns the Formation Evaluation Assurance contract into a deterministic CEPIO runtime path. It executes the five PET-02 skills against a resolved evidence package, applies CEPIO runtime/type/policy preflight before reasoning, fails closed on insufficient evidence or conflicting authority, and emits one machine-verifiable answer object.

The reference question remains:

> **Show me the authoritative formation evaluation for Well A-17, Zone B. Explain why it changed, what evidence supports or contradicts it, what remains uncertain, and which current models, reserves cases, opportunities or decisions would be affected if the interpretation is wrong.**

## Benchmark provenance

The public A-17 / Zone B benchmark is **synthetic and CEPIO-authored**. It is not sourced from Aramco, another operator, a commercial petrophysics dataset, or a published field case.

Its construction deliberately combines domain-realistic relationships:

- `Rw` and Archie-parameter changes that matter to saturation interpretation;
- porosity and saturation cutoffs that matter to net-reservoir/net-pay classification;
- a log-derived permeability transform that can be challenged by routine core analysis;
- pressure evidence that can support or challenge a fluid-contact interpretation;
- downstream dependence from formation evaluation into static models, reservoir models, reserves, opportunities and decisions.

The numbers are chosen as deterministic test fixtures, not as empirical industry reference values. The benchmark file now carries explicit provenance metadata stating `source_dataset: none`, `fictional_identifiers: true`, its intended test use and its limitations.

## Execution architecture

```text
Resolved PET-02 evidence package
            |
            v
      CEPIO Runtime
  TypeRegistry + Policy
            |
            v
   Five Skill preflights
            |
      READY only
            v
FormationEvaluationAssuranceRuntime
            |
   +--------+---------+---------+---------+
   |        |         |         |         |
 context   delta   assumptions reconcile  impact
   |        |         |         |         |
   +--------+---------+---------+---------+
            |
            v
 Pet02ExecutionResult
```

The runtime does not calculate petrophysical properties. It evaluates the governance and reasoning context around technical outputs produced elsewhere.

## Skill admission

Before a PET-02 answer is produced, all five skills are registered with `SkillRegistry` and evaluated using CEPIO's runtime-aware preflight boundary.

The preflight verifies:

- canonical CEPIO object-type identities exist;
- required relationships are registered and semantically traversable;
- the actor can read governed evidence and target types;
- the five skills are bound to the PET-02 runtime contract;
- the runtime fails closed if a skill is not READY.

The reference actor role is `petrophysicist`. The role has read access only to the PET-02 semantic surfaces required for the journey: formation-evaluation case/state, petrophysical characteristics, evidence, assumptions, uncertainty, confidence, dependency and well context. It has no action, function or decision permissions in this increment.

## Runtime stages

### 1. Formation Evaluation Context

The runtime resolves the requested well/interval, the single authoritative case, supersession lineage and versioned evidence inventory.

Failure states include:

- requested context absent;
- no authoritative case;
- multiple authoritative cases;
- missing predecessor referenced by `supersedes`;
- incomplete external source/version identity.

### 2. Interpretation Delta

The runtime computes changed assumptions and changed findings directly from current and superseded case content. It does not copy the benchmark's expected-answer section.

### 3. Assumption Trace

The runtime exposes the active interpretation assumptions and all explicit uncertainty assessments, including their material drivers.

### 4. Core–Log Reconciliation

Evidence is separated into supporting and contradictory evidence while preserving external identity/version. Contradictory evidence is not averaged away or rewritten.

### 5. Downstream Impact

The runtime traverses the dependency graph transitively from the authoritative formation-evaluation case and returns current affected static models, reservoir models, reserves cases, opportunities and decisions.

## Result contract

The answer contains:

```text
status
question
preflights[]
trace[]
blockers[]
answer
  |- authoritative_case
  |- authority_state
  |- superseded_case
  |- changed_assumptions[]
  |- changed_findings[]
  |- active_assumptions
  |- current_findings
  |- supporting_evidence[]
  |- contradictory_evidence[]
  |- uncertainty[]
  |- confidence[]
  |- downstream_impact[]
  |- recommended_actions[]
  |- human_authority_required
  `- prohibited_ai_conclusions[]
```

Status semantics are:

- `ANSWERED` — runtime admission and instance evidence are sufficient for the deterministic assurance answer;
- `INSUFFICIENT_CEPIO_EVIDENCE` — semantic/policy admission or required instance evidence is incomplete;
- `AUTHORITY_CONFLICT` — more than one formation-evaluation case is marked authoritative.

## Authority boundary

PET-02 v0.2 can recommend a technical review or information-gain activity. It cannot:

- declare a new interpretation authoritative;
- approve a reserves basis;
- overwrite OSDU/ADME or other external technical records;
- approve an investment or well decision.

The reference output therefore keeps `human_authority_required: true`.

## Reference execution

```bash
PYTHONPATH=src python scripts/run_pet02_formation_evaluation.py \
  --well A-17 \
  --interval Zone-B \
  --fail-on-non-answer
```

The command emits the complete `Pet02ExecutionResult` as JSON.

## Executable assets

- `src/cepio/formation_evaluation.py`
- `scripts/run_pet02_formation_evaluation.py`
- `generalization/competency/subsurface-petrophysics-pet02-runtime-v0.2.yaml`
- `generalization/benchmarks/subsurface-petrophysics-pet02-a17-zone-b.yaml`
- `tests/test_petrophysics_pet02_runtime.py`

## What v0.2 proves

v0.2 proves that CEPIO can execute a governed, deterministic persona reasoning journey over a resolved synthetic evidence package while preserving the OSDU-first architecture and human authority boundary.

It does **not** yet prove live ADME/OSDU connectivity. The next integration step is to replace the benchmark data-package resolver with runtime bindings that hydrate the same logical input contract from Wellbore DDMS, RAFS DDMS and customer-profile interpretation/pressure repositories. The reasoning and answer contract should remain unchanged.

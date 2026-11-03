# CEPIO cross-domain evidence-to-decision regression v0.1

**Status:** Proposed public deterministic reference; **not** an Industry IQ uplift, live integration, human-approval or field-qualification claim.

## Product rationale

CEPIO's Product North Star is the most trusted AI companion for every industry professional. Its moat is an independently qualified Industrial Competence Network, not a catalogue of scenarios or an ingestion platform. This reference challenges one reusable operating pattern across different professions: consequential evidence should provoke an appropriately governed reassessment, never be silently ignored or promoted directly into an authorized action.

## What is reused

- generalization/runtime/refinery-operating-abstraction-v0.1.yaml: K-201 evidence, consequence, work/permit and assigned authority context.
- generalization/runtime/subsurface-reservoir-engineering-runtime-v0.1.yaml: challenged reservoir hypothesis, model supersession, downstream decision dependency, and recommendation/decision distinction.
- cepio.runtime_coverage.run_runtime_question: the existing deterministic runtime evidence/probe evaluator, including the fail-closed fabricated-evidence control.

The small public manifest at generalization/regression/evidence-decision-reassessment-v0.1.yaml selects existing probes. It **does not** create a new agent runner, source adapter, database, simulation engine, ontology class or Industry IQ qualification authority.

## Scope and negative controls

For each domain the checks demonstrate that selected existing evidence, consequence and governance *graph paths* are resolvable. They then deliberately remove one required evidence link and one consequence link and assert that the same runtime test fails. These deterministic fixtures have no customer data, live telemetry, numerical simulation, actual approval or external writeback.

This is **not** yet a test of whether an agent notices the change and revises its recommendation. It also does not prove that a human approved an action merely because an authority or Decision object is represented. An independent, protected evaluation with matched model and evidence/tools is needed to establish actual Industry IQ uplift. Protected casebooks and sealed holdouts belong in CEPIO-Labs, not the public repository.

## Local tests

    PYTHONPATH=src pytest -q tests/test_evidence_decision_reassessment_v01.py

## Next qualification gate (outside this PR)

Execute controlled, matched-model, matched-evidence tests **with CEPIO vs without CEPIO**. Evaluate correct detection of changed/conflicting evidence, unsupported recommendations, source-specific evidence freshness, authorization, uncertainty and expert review burden. Progress only when independently reviewed, rights-cleared evidence demonstrates uplift; the Capability Registry and v1 scorecard require separate governed updates. No automatic global learning from customer data or outcomes.

**Release guardrail:** CEPIO v0.5 CONNECT remains gated on three authoritative live source domains and a governed, verified and reconciled writeback. This offline regression does not satisfy that gate.

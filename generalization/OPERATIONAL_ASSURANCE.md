# CEPIO Operational Assurance

Semantic capability and operational assurance are separate gates.

## Gate 1 — Semantic capability

The capability harness asks whether CEPIO has an approved semantic composition for a business question. It is deterministic and ontology-based. The drilling persona pack v0.3 currently proves semantic capability for all 14 frozen questions.

## Gate 2 — Operational assurance

Operational assurance asks whether CEPIO can support claims with executable runtime evidence. The first v0.4 drilling fixture covers five gates:

1. **Temporal** — reconstruct valid-time state as CEPIO knew it at different transaction times.
2. **Provenance** — explain a property through source record, observation time, mapping version and transformation run.
3. **Authority** — resolve the current authority holder through an explicit scoped `AuthorityAssignment`, not a direct permanent person-to-asset shortcut.
4. **Policy + kinetic** — prove that an AI recommender is blocked from execution, a permitted human can execute, and the resulting audit preserves the originating `Decision`.
5. **Operator evidence discipline** — accept answers only when every cited evidence ID exists in the current CEPIO evidence bundle; unsupported citations fail closed.

The initial v0.4 fixture is intentionally narrower than the 14-question semantic pack. It proves the assurance protocol across representative critical capabilities before expanding runtime coverage question by question.

## Evidence rule

`LLM inference != enterprise fact`

An agent may plan, summarize or explain. Enterprise claims must be supported by CEPIO evidence records. If evidence is insufficient, the required answer is `INSUFFICIENT_CEPIO_EVIDENCE`.

## Metrics

CI reports semantic capability and operational assurance separately. A 100% semantic score does not imply runtime or production readiness. Future assurance expansion should track:

- runtime answerability
- valid-time and transaction-time correctness
- provenance completeness
- authority resolution
- policy enforcement
- decision/action/audit continuity
- source independence
- operator evidence discipline

## Expansion path

After the v0.4 protocol is stable, extend deterministic runtime fixtures across the remaining drilling persona questions, then repeat the same assurance model for refinery and power archetypes. Live LLM Operators can be introduced later against the same evidence contract without becoming the pass/fail authority.

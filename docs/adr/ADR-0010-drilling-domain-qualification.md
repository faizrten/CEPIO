# ADR-0010: Freeze the drilling domain-qualification benchmark

Status: Accepted

## Context

Drilling-contractor competency coverage needs to extend beyond the v0.2 persona expansion and v0.3 capability benchmark into enterprise performance, optimization, contract delivery, and governed agent operations. The challenge must create useful semantic pressure without changing canonical ontology semantics or turning a benchmark vocabulary list into a remediation plan.

## Decision

Freeze `drilling-contractor-domain-qualification-v0.4` as a separate, versioned domain artifact. Additive persona expansion v0.3 introduces seven enterprise, performance/optimization, contracts, and digital/AI roles. The nine questions use operating language, are grouped into enterprise, operational-optimization, and agentic-operations bands, and validate against approved semantic alternatives.

Keep the initial CORE gap triage as a separate accepted artifact. Pin the competency-pack fingerprint and expected baseline in regression tests so changes to questions, alternatives, coverage, or intentional semantic pressure are explicit. Preserve all prior persona/competency versions and their historical reports.

## Governance and boundaries

- The benchmark is not a CEPIO product release and adds no canonical ontology vocabulary.
- Classify gaps as CORE, DOMAIN, PROFILE, MAPPING, or REJECT before implementation; remediate in the layer that owns the semantics.
- Do not edit a frozen pack to match an ontology change. A changed challenge receives a new pack version.
- Semantic readiness does not prove policy authorization, provenance completeness, or runtime action safety. Those remain separate runtime qualifications.
- The isolated qualification workflow runs the focused test and deterministic harness and publishes only CI evidence artifacts. Existing CI, quality, governance, and CodeQL gates remain unchanged.
- Publication classification is **PROTECTED — public abstraction only**. No customer data or copyrighted standards content is included.

## Consequences

The v0.4 baseline is 7 PASS / 1 PARTIAL / 1 FAIL with 81.8% semantic-check coverage. The two optimization gaps remain visible and classified as CORE rather than prompting vocabulary additions. The batch and ontology hashes in retained reports make later results comparable to this frozen challenge.

## Validation

Focused tests check additive persona coverage, frozen pack fingerprint, all three challenge bands, clean persona/standard references, initial gap triage, and intentional semantic pressure. The separate workflow runs the frozen benchmark and retains its JSON report.

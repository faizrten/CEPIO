# ADR-0044 — Sovereign Compounding Industrial Intelligence

- **Status:** Proposed for architecture and publication review
- **Date:** 2026-10-24
- **Decision scope:** Global reusable industrial competence vs enterprise-owned operational intelligence
- **Classification:** PUBLIC architecture; protected implementation and customer-specific records remain outside this repository

## Context

CEPIO's industrial capability must improve through reusable qualification and cross-domain generalization without pooling customer-confidential state, memorized traces, private model adaptations, business logic, derived synthetic records or decisions. The existing [ADR-006](ADR-006-enterprise-knowledge-sovereignty.md) governs enterprise-owned truth; [ADR-007](ADR-007-open-interface-protected-intelligence.md) governs whether CEPIO-owned intelligence is safe and justified to publish. The Capability Registry already demands reusable cross-domain evidence and human release review.

The North Star therefore makes the business/design objective explicit: **Collective industrial progress. Sovereign enterprise intelligence.** The public product should express this objective and its testable governance implications without exposing protected CEPIO Labs methods or customer records.

## Decision

1. **Global reusable competence** means source-neutral Industry IQ contracts, independently authored/authorized domain methods, and evidence-backed capability releases, not consolidated customer memory.
2. **Tenant intelligence stays tenant-scoped**: source records, investigations, customer embeddings/models, operational thresholds, work methods, decisions, outcomes and derivatives remain within their authorized enterprise boundary. Permitted use for one task does not imply global learning or cross-tenant publication.
3. **Opt-in contributions are separately governed**: explicit source rights, purpose and scope, provenance/derivation lineage, IP/confidentiality and disclosure review, independent technical qualification and accountable human approval. Unknown, missing or expired permission means deny.
4. **Synthetic content is not automatically safe**: simulators and reviewed independent scenarios can qualify generic ability, but derived customer-style data do not escape their original restrictions merely by using fictional identifiers or adjusted values.
5. **Release and scoring remain evidence-based**: customer/agent boundaries, evaluator isolation, model-provider traces and approval checks must be enforced and tested before production claims. No new maturity score is awarded solely for this architecture decision.

## Existing controls are preserved

- ADR-006/007, binding contracts, per-tenant policy and authority paths remain the controlling source boundaries.
- The Capability Registry retains independent two-domain evidence, full configured regression survival and explicit human architecture approval; the new doctrine does **not** auto-promote evidence.
- Existing release, source-authoritative and verified writeback requirements are unchanged.
- The 100-point canonical score and pinned **69/100** baseline are unchanged; supplemental competence-compounding and sovereignty-assurance indicators are **non-scoring**.
- **Existing gates remain enforced.** This ADR creates no exception to governed execution, source permissions, CEPIO CI, CodeQL, quality, public-IP classification or human reviews.

## Public/protected placement

Public CEPIO contains only interoperable operating contracts, architecture and qualified claims. Protected CEPIO Labs owns scenario generation, protected evaluation, held-out truth, industrial expertise implementation and private qualification. Customer-specific context and derivative intelligence remain customer-controlled. PostgreSQL may persist authorized metadata per security boundary; it is not a shared customer knowledge pool and no actual PostgreSQL schema or production storage behavior is introduced by this ADR.

## Validation and rollout

This PR is documentation/governance only: review the diff for confidential assets, verify that `config/v1-scorecard.yaml` changes only North Star prose and not scoring evidence/weights, run governance-protection and quality/CI/CodeQL, and obtain normal review. Subsequent runtime work must deliver fail-closed negative tests for cross-tenant retrieval, embeddings and caches, unauthorized global learning, expired rights, hidden evaluator leakage and forged human decisions.

## Alternatives rejected

- Shared pooled customer operational data as the default network effect: violates enterprise sovereignty.
- Treat any synthetic or anonymized derivative as safe for cross-customer reuse: rights and leakage risks persist.
- Treat documentation as verified operational enforcement: would overstate product readiness.
- Introduce a proprietary data platform or new service purely for sovereignty: conflicts with Thin Core / Thick Industry IQ doctrine.

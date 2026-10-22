# ADR-0037 — Open CEPIO Platform, Private Industry IQ

**Status:** Accepted — 2026-10-22 (founder direction)
**Classification:** PUBLIC architectural boundary
**Supersedes:** ADR-0036's proposed full-repository privacy, while retaining its caution about historical public exposure.

## Context
CEPIO aims to become the common interoperability and governed operating contract for industrial professionals. The existing public repository includes source-neutral runtime and contracts alongside differentiated domain logic and evaluation artifacts. `CEPIO-Labs` is already private and contains protected IQ packs, test corpora and strategic roadmap information. Full repository privacy would constrain adoption and change current GitHub/Azure entitlements; unconstrained public development would erode the industrial competence moat.

## Decision
1. Keep `faizrten/CEPIO` public as the installable, source-neutral semantics/API/MCP/SDK and governed-action runtime.
2. Keep `faizrten/CEPIO-Labs` private for specialist industrial reasoning, differentiated Skills, evaluation/benchmarks, learning/normalization and proprietary performance intelligence. Customer-owned material stays in customer-controlled boundaries.
3. Replace the blanket public-code embargo with a **fail-closed protected-path rule** and PR IP classification/attestations for other public code. Classify all new industrial intelligence as private unless narrowly approved for release.
4. The public source package must run without private source or private CI access. Private Industry IQ consumes stable public Capability/Skill/Performance contracts. Governed external writebacks continue to be authorized, verified and audited by CEPIO.
5. Any historically public source is treated as previously disclosed; private-copy migration protects future derivatives and incremental investment but does not erase the old public history.
6. Remove public differentiated implementation only after a private substitute has equivalent interfaces and tests. Never remove public CI fixtures or module imports merely to satisfy an IP inventory.

## Wave-1 candidate
Copy `generalization/gaps/drilling-contractor-persona-v0.2-resolutions.yaml` into the protected Labs remediation ledger, preserving exact content and provenance. Search found no direct filename references in the public CEPIO code index. Remove the public tip copy only after private copy is merged and the full public CI suite passes, without purporting to undo historical disclosure.

## Guards
- Protected public paths: detailed `generalization/` agent/competency/benchmark/runtime/gap/normalization assets, full `mvp/datasets/`, `profiles/` and selected differentiated `src/cepio/` implementation modules.
- Public paths: versioned generic contracts, standards-aligned ontology, API/MCP/SDK, source-neutral policy, approved samples and platform QA.
- Open source licensing is a deliberate separate legal decision. Public visibility itself does not grant unrestricted license rights.
- Public classification automation does not inspect source contents for every conceivable secret, so security/code scanning and human IP review remain required.

## Validation and deployment
Keep CI/quality/CodeQL/governance required checks and Azure deployment workflows unchanged unless separately qualified. No physical Azure resources, credentials or Foundry inference settings are modified by this governance decision. Test protected-path rejects and PUBLIC generic code allowances; verify public CI after any actual removal.

## Rollback
If a protected-path check misclassifies legitimate public infrastructure, amend the path pattern through high-risk governance PR and documented ADR, never force-push public `main`.

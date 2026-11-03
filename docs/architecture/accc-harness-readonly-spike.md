# ACCC v0.1 — read-only harness adapter execution contract (candidate)

Status: **design and test specification only**. No runtime implementation, live qualification, inference, deployment or release change is claimed.

## Objective

Prove a minimal provider-neutral Adaptive Context & Competence Composition (ACCC) plan against existing CEPIO contracts, then optionally expose it to Microsoft Agent Framework as a read-only host tool. Do not create a new agent loop, memory store, Skill registry, capability registry, pack resolver, policy authority or ontology.

## Verified reuse seams

- `src/cepio/capability_routing.py`: `CapabilityRouter.route(RetrievalIntent)` ranks registry candidates using explicit hints and lexical matches; **relevance is not qualification**.
- `src/cepio/retrieval_runtime.py`: `RetrievalPlanner`, `RetrievalEngine`, `RetrievalContextPipeline` assemble bounded context; no assumption of current source truth.
- `src/cepio/memory.py`: `MemoryStore` and `ContextAssembler` implement scope, expiry and budget checks.
- `src/cepio/capability_registry.py`: `CapabilityRegistry`, `CapabilityRecord` carry maturity, evidence, domains, authority and uncertainty descriptors; customer evidence cannot justify global capability promotion.
- `docs/industry-iq-pack-registry.md`: deterministic pack SemVer, dependency, cycle and collision checks.
- `src/cepio/skill_preflight.py`: runtime/actor Skill READY/BLOCKED admission; READY **does not** prove target-instance evidence sufficiency.
- Existing Application Contract / REST / MCP: use host-owned identity; never trust an agent-supplied tenant or role.

## Proposed contract (not yet implemented)

`compose_readonly(request, trusted_host_context) -> CompositionResult`

Request: task text, asset/object reference, decision objective, optional capability hints, context budget, max plan steps. Host context: authenticated actor/tenant, approved provider bindings, allowed tools, policy/version, current time, request correlation ID. The model cannot author host context.

Result: `READY | BLOCKED | NEEDS_EVIDENCE`; selected capability and Skill IDs with exact versions and qualification ceilings; source evidence IDs and freshness; required-but-missing evidence; compatibility/uncertainty blockers; bounded proposed **read-only** steps; rejection reasons; stable composition manifest hash and provenance references. No prose-only permission decisions.

### Admission pipeline

1. Validate authenticated host context and tenant boundary.
2. Route candidate capabilities using existing router; reject unresolved required IDs.
3. Filter by independently supported maturity/validated scope and actor authority. Never treat lexical score as admission.
4. Retrieve and assemble authorized context using existing pipeline; preserve stale/conflicting/missing state.
5. Resolve pack compatibility and invoke Skill preflight through trusted runtime.
6. Validate composition-level input/output types, units, physical assumptions, model lineage, uncertainty dependencies and declared operating envelope. Unknown compatibility -> BLOCKED/NEEDS_EVIDENCE, never optimistic READY.
7. Return a version-pinned read-only plan and receipt; no external writes, approvals, permit issuance or runtime execution.

A `READY` composition means the *plan* is admissible for further host review, not that a diagnosis, recommendation, production operation or source write is authorized.

## Microsoft Agent Framework integration seam

A thin optional host adapter may register a read-only `cepio_compose_context_and_competence` tool and a CEPIO-authorized context provider. The adapter passes trusted identity from the host, not the prompt; delegates admission to CEPIO; returns typed status and evidence references. Do not expose generic shell, web, arbitrary file access, auto-approved tools or write Actions. Preserve a provider-neutral ACCC interface so a different harness can replace Microsoft without changing Industry IQ contracts.

## First negative and positive cases (offline, no paid inference)

| Case | Expected |
| --- | --- |
| K-201 consistent authorized evidence + compatible read-only Skill | READY plan only, no action |
| K-201 conflicting same-time measurements | NEEDS_EVIDENCE or BLOCKED; contradiction retained |
| K-201 missing entire required observation | NEEDS_EVIDENCE; no fabricated measurement |
| Reservoir R3 superseded model / incompatible assumptions | BLOCKED; model lineage retained |
| Reservoir R3 probabilistic alternative with incomplete calibration | Explicit quantitative and qualitative uncertainty, no deterministic truth |
| Rig wrong-shift crew, invented identity, wrong-task permit | BLOCKED |
| Issued permit treated as permission to work | BLOCKED |
| Wrong tenant, revoked source rights or expired memory | BLOCKED; no disclosure |
| Unregistered Skill, pack-version mismatch, preflight BLOCKED | BLOCKED |
| Prompt requests write, tool bypass or higher authority | BLOCKED; no execution |
| Missing required context under budget | NEEDS_EVIDENCE/BLOCKED; no silent truncation |
| Two incompatible methods / units | BLOCKED; no composition |

## Evidence and acceptance

Stage A: deterministic tests for all cases, no external calls. Stage B: independent K-201/R3 review and fresh sealed holdouts, separate from authored development fixtures. Stage C: matched baseline vs ACCC vs harness-only with fixed model/data/tools, actual receipts, safety errors, latency, cost and expert review burden. No uplift, field value or v0.5 CONNECT credit from a passing synthetic test.

## Governance and scope

Keep protected benchmarks and reviewer/customer information out of public Core. No inference spend, Azure provisioning, auth/permission changes, production deployment or source write. Govern implementation via separate PR(s) and required CI/security review. v1 canonical score, proposed unscored v2 rubric and published v0.4 remain unchanged.


## Implementation checkpoint — 2026-11-03

The draft branch now contains `src/cepio/accc_readonly.py` and `tests/test_accc_readonly.py`. The implementation is a **deterministic offline baseline**, not the full contract described above. It reuses CapabilityRouter and CapabilityRegistry, performs host-asserted admission filtering, returns READY/BLOCKED/NEEDS_EVIDENCE, and hashes admitted capability/Skill IDs and registry version. The hash is **not** a complete execution receipt or cryptographic proof of authenticated evidence.

`HostBoundComposer` deliberately receives only the untrusted task request from an agent-facing caller and obtains `TrustedAdmission` from a host-owned resolver. However, **the resolver is not yet implemented against real CEPIO identity, SkillRegistry.preflight, source freshness and policy checks**. Direct `ReadOnlyComposer.compose` must remain test-only; an untrusted caller can forge its admission object. No MCP or REST registration is allowed until host identity binding, actor/tenant enforcement, source validity and negative tests are implemented and reviewed.

The current coordinator does not yet invoke `RetrievalContextPipeline`, resolve real pack deployment versions, validate physical units/assumptions, propagate reservoir uncertainty or create a complete provenance receipt. It must not be promoted to Core or described as independent assurance. CI and security checks must be evaluated on the latest head SHA before merge.

# Version naming and delivery status

CEPIO product releases, roadmap capability labels, component iterations, benchmark contracts and API versions are independent version axes. Always name the owner of a version.

## Product roadmap labels

CEPIO product releases use a short **capability label** plus a descriptive subtitle. The label communicates the proof that the release must establish; the subtitle describes the implementation focus.

| Product release | Capability label | Descriptive subtitle | Product proof |
| --- | --- | --- | --- |
| CEPIO v0.4 | **FOUNDATION** | Developer Preview | Developers can build against a coherent CEPIO operating contract |
| CEPIO v0.5 | **CONNECT** | Live Industrial Integration | CEPIO can operate over authoritative industrial systems |
| CEPIO v0.6 | **EXECUTE** | Kinetic Runtime + Reference Industrial Applications | CEPIO can produce governed, verified industrial outcomes |
| CEPIO v0.7 | **EXTEND** | Industrial Developer Platform | Independent teams can add Industry IQ without modifying Core |
| CEPIO v0.8 | **OPERATE** | Enterprise Runtime | Enterprises can depend on CEPIO for sustained critical workloads |
| CEPIO v0.9 | **GENERALIZE** | Portability + Second-Enterprise Adoption | CEPIO and its Industry IQ remain reusable across enterprises/platforms |
| CEPIO v1.0 | **GUARANTEE** | Production Guarantees | CEPIO exposes stable, explicit production contracts |

Preferred display form:

`CEPIO v0.5 CONNECT — Live Industrial Integration`

Short form where space is constrained:

`v0.5 CONNECT`

The capability label is a product-roadmap label, **not** a separate semantic version or package version.

## Other naming conventions

| Scope | Display form | Meaning |
| --- | --- | --- |
| Product release | `CEPIO v0.5 CONNECT` | Target operating capability; completion requires the release gate |
| Runtime component | `Kinetic external verification v0.4` | Version of the named component contract/slice |
| Lab benchmark | `Drilling domain qualification v0.4.1` | Frozen benchmark/normalization contract |
| Skill component | `Skill dispatch v0.2.3` | Named Skill subsystem iteration |
| Ontology module | Module name + declared version | Compatibility/dependency contract from `ontology-modules.yaml` |
| Public API | `API v1` / `/api/v1` | Interface compatibility major; independent of product/package minor |

Do not infer a CEPIO product release from a Lab score, Skill version, runtime slice or ontology-module version. Preserve frozen benchmark identifiers, historical measurements, filenames, branches, tags and package/module versions.

## GitHub issue titles

Roadmap epic titles should use the capability label:

- `[Roadmap][CEPIO v0.5 CONNECT] Live Industrial Integration`
- `[Roadmap][CEPIO v0.6 EXECUTE] Kinetic Runtime + Reference Industrial Applications`
- `[Roadmap][CEPIO v0.7 EXTEND] Industrial Developer Platform`
- `[Roadmap][CEPIO v0.8 OPERATE] Enterprise Runtime`
- `[Roadmap][CEPIO v0.9 GENERALIZE] Portability + Second-Enterprise Adoption`
- `[Roadmap][CEPIO v1.0 GUARANTEE] Production Guarantees`

Other issue title conventions remain independent:

- Product work: `[CEPIO v0.5][P0] Integration adapter SDK and connector contract`
- Parallel runtime epic: `[Runtime][P0] Kinetic runtime and workflow orchestration`
- Lab work: `[Lab][Drilling domain v0.4.1] Runtime and operational qualification`
- Unscheduled work: `[Backlog][P1] Purview governance and lineage bridge`

Do not force capability labels onto independently versioned runtime, Lab, Skill or ontology artifacts. A work item can support `CONNECT` or `EXECUTE` without being renamed to the product release version.

## Status is separate from version and capability label

Use `current`, `future`, `parallel/partial`, `parked` and `completed` to describe delivery status.

Examples:

- `CEPIO v0.4 FOUNDATION — Developer Preview` — **completed / qualified**;
- `CEPIO v0.5 CONNECT — Live Industrial Integration` — **current**;
- `CEPIO v0.6 EXECUTE` through `v1.0 GUARANTEE` — **future product gates**, even where foundations have been pulled forward.

A capability label describes **what must be proven**, not whether the proof is complete. An open PR or a component implementation does not qualify a product release.

## Current reviewed baseline

- **v0.4 FOUNDATION — Developer Preview:** qualified through #69; historical umbrella #22 completed.
- **v0.5 CONNECT — Live Industrial Integration:** current roadmap epic #51; real SAP/PI/writeback qualification remains.
- **v0.6 EXECUTE — Kinetic Runtime + Reference Industrial Applications:** future product gate #59, with substantial runtime foundations already pulled forward.
- **v0.7 EXTEND — Industrial Developer Platform:** future #60.
- **v0.8 OPERATE — Enterprise Runtime:** future #61.
- **v0.9 GENERALIZE — Portability + Second-Enterprise Adoption:** future #62.
- **v1.0 GUARANTEE — Production Guarantees:** future #63.
- Independently versioned Generalization Lab, domain, runtime and Skill work continue in parallel.
- #20/#25 remain parked with no current product release target.

## Labels and milestones

The roadmap capability words (`FOUNDATION`, `CONNECT`, `EXECUTE`, `EXTEND`, `OPERATE`, `GENERALIZE`, `GUARANTEE`) are **product taxonomy**, not necessarily GitHub label objects. Title prefixes and documentation provide the canonical classification even when repository label administration is unavailable.

If GitHub labels are later created, keep dimensions separate:

- release capability: `connect`, `execute`, etc.;
- purpose: `epic`, `implementation`, `qualification`, `backlog`;
- delivery status: `active`, `partial`, `future`, `parked`;
- priority: existing priority convention;
- component/Lab versions: remain in their own version axes.

Avoid a single label that conflates release, purpose, priority and status.

## Compatibility and evidence

This naming convention does not replace API, ontology or package compatibility policy. Never renumber a component or benchmark merely to align it with a roadmap milestone. Record the named artifact, exact version, relevant implementation/promotion PRs and qualification status. Closed historical issues retain their original titles as evidence.

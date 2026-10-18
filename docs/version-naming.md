# Version naming and delivery status

CEPIO product releases, component iterations, benchmark contracts and API versions are independent version axes. Always name the owner of a version.

## Naming convention

| Scope | Display form | Meaning |
| --- | --- | --- |
| Product release | CEPIO v0.5 | Target operating capability; completion requires the release gate |
| Runtime component | Kinetic external verification v0.4 | Version of the named component contract/slice |
| Lab benchmark | Drilling domain qualification v0.4.1 | Frozen benchmark/normalization contract |
| Skill component | Skill dispatch v0.2.3 | Named Skill subsystem iteration |
| Ontology module | Module name + its declared version | Compatibility/dependency contract from ontology-modules.yaml |
| Public API | API v1 / /api/v1 | Interface compatibility major; independent of product/package minor |

Do not infer a CEPIO release from a Lab score or component version. Generalization Lab v0.7 in historical records does not mean CEPIO v0.7 Developer Platform shipped. Preserve frozen benchmark identifiers, historical measurements, filenames, branches, tags and package/module versions.

## GitHub issue titles

- Product work: `[CEPIO v0.5][P0] Integration adapter SDK and connector contract`
- Product epic: `[Roadmap][CEPIO v0.6] Reference Industrial Applications`
- Parallel runtime epic: `[Runtime][P0] Kinetic runtime and workflow orchestration`
- Lab work: `[Lab][Drilling domain v0.4.1] Runtime and operational qualification`
- Unscheduled work: `[Backlog][P1] Purview governance and lineage bridge`

Retain an established priority where one exists. Do not invent a product release target for independently tracked Lab work or parked backlog. Runtime #67 supports current CEPIO v0.5 integration foundations and the CEPIO v0.6 application target; its component slice versions are separate.

For PR titles retain the existing conventional prefix, then name the version owner: `feat(lab): qualify drilling domain benchmark v0.4.1 at runtime`. A dependency PR uses the dependency's own version.

## Status is separate from version

Use current, future, parallel/partial, parked, and completed to describe delivery. A version in a title denotes scope/target, not proof of release. An open PR is proposed work; feature-branch merges require mainline promotion evidence. Qualified product capability is separate from a GitHub Release or published package.

Current reviewed baseline:
- CEPIO v0.4 Developer Preview qualified through #69; #22 completed.
- CEPIO v0.5 Live Industrial Integration is current (#51), with real SAP/PI/writeback qualification remaining.
- CEPIO v0.6–v1.0 remain future roadmap (#59–#63).
- Kinetic runtime #67 is partially implemented on main and developed in parallel.
- Drilling domain qualification #112/#116/#119 remains in an open PR stack.
- #20/#25 remain parked with no current product release target.

## Labels and milestones

The connected tools support applying existing labels but do not expose label creation or milestone administration; the label/milestone catalog endpoints are unavailable. Title prefixes and issue-body scope fields provide consistent classification now. They are not newly created GitHub labels.

When administration is available, use one product-release milestone per issue only when a release target is agreed. Keep purpose, delivery status, priority and component/benchmark version distinct; reuse established label names rather than creating overlapping version labels.

## Compatibility and evidence

This naming convention does not replace API, ontology or package compatibility policy. Never renumber an artifact merely to align it with a roadmap milestone. Record the named component/benchmark, its exact version, relevant implementation/promotion PRs, and qualification status. Closed historical issues retain their original titles as evidence.

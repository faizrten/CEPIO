# Version naming and delivery status

CEPIO product releases, component iterations, benchmark contracts, packs and API versions are independent version axes. Always name the owner of a version.

## Product release taxonomy

CEPIO product releases use a capability label that states the proof required from that release:

| Product release | Capability label | Release proof |
| --- | --- | --- |
| **CEPIO v0.4** | **FOUNDATION** | developers can build against a coherent governed CEPIO contract |
| **CEPIO v0.5** | **CONNECT** | CEPIO can operate over authoritative industrial truth and close one governed external loop |
| **CEPIO v0.6** | **EXECUTE** | CEPIO can produce governed, verified industrial outcomes through reference applications |
| **CEPIO v0.7** | **EXTEND** | independent teams can add Industry IQ safely through supported contracts/tooling |
| **CEPIO v0.8** | **OPERATE** | an enterprise can depend on CEPIO operationally |
| **CEPIO v0.9** | **GENERALIZE** | CEPIO is portable across materially different enterprises/platform contexts |
| **CEPIO v1.0** | **GUARANTEE** | CEPIO provides stable production contracts and explicit guarantees |

The capability label is part of product-roadmap language. It is **not** another semantic-version axis and must not be copied onto unrelated component, Lab, ontology or pack versions.

Canonical display forms:

- `CEPIO v0.4 FOUNDATION — Developer Preview`
- `CEPIO v0.5 CONNECT — Live Industrial Integration`
- `CEPIO v0.6 EXECUTE — Governed Industrial Outcomes`
- `CEPIO v0.7 EXTEND — Industrial Developer Platform`
- `CEPIO v0.8 OPERATE — Enterprise Runtime`
- `CEPIO v0.9 GENERALIZE — Multi-Enterprise Portability`
- `CEPIO v1.0 GUARANTEE — Production Guarantees`

## Version scopes

| Scope | Display form | Meaning |
| --- | --- | --- |
| Product release | `CEPIO v0.5 CONNECT` | target operating capability; completion requires the product release gate |
| Runtime component | `Kinetic external verification v0.4` | version of the named runtime component contract/slice |
| Industry IQ pack | `Industry IQ pack v0.x` or pack ID/version | distributable reusable industrial intelligence contract |
| Performance reference pack | pack ID/version | reusable organization-neutral performance semantics |
| Lab benchmark | `Drilling domain qualification v0.4.1` | frozen benchmark/normalization/qualification contract |
| Skill component | `Skill dispatch v0.2.3` | named Skill subsystem iteration |
| Ontology module | module name + declared version | compatibility/dependency contract from `ontology-modules.yaml` |
| Application/management contract | named contract + version | protocol-neutral public/control-plane contract |
| Public API | `API v1` / `/api/v1` | interface compatibility major; independent of product/package minor |
| MCP surface | named MCP contract/profile | protocol projection; does not define product release version |

Do not infer a CEPIO product release from a Lab score, pack version, application-contract version, runtime slice or repository feature.

Historical identifiers remain immutable evidence. Generalization Lab v0.7 in historical records does not mean CEPIO v0.7 EXTEND shipped. A Skill or Industry IQ pack at v0.6 does not mean CEPIO product v0.6 EXECUTE is qualified.

## Product release status vs mainline capability

Version and status are separate.

Use these delivery terms:

- **qualified** — release/gate has its required evidence;
- **current / partial** — active product release gate with some mainline foundations but incomplete proof;
- **future** — product release gate not yet current/qualified;
- **implemented on main** — component/capability exists in repository mainline, but this does not qualify a product release;
- **live-qualified** — a real environment/integration proof exists when the contract specifically requires one;
- **planned / parked** — scoped work not currently qualified/delivered.

Current product baseline as of 2026-10-20:

- **CEPIO v0.4 FOUNDATION — Developer Preview:** qualified.
- **CEPIO v0.5 CONNECT:** current / partial; live SAP/PI + three-source + governed writeback proof remains open.
- **CEPIO v0.6 EXECUTE:** future release gate; substantial kinetic/Skill/application foundations already exist on `main`.
- **CEPIO v0.7 EXTEND:** future release gate; developer/platform and Industry IQ extension foundations already exist on `main`.
- **CEPIO v0.8 OPERATE:** future release gate; governance, deployment, observability and reliability foundations exist but enterprise HA/SLO/DR qualification remains open.
- **CEPIO v0.9 GENERALIZE:** future release gate; semantic/runtime generalization evidence exists, but real second-enterprise adoption is not qualified.
- **CEPIO v1.0 GUARANTEE:** future release gate.

See [`current-state.md`](current-state.md) for the dated mainline snapshot.

## GitHub issue-title convention

Product roadmap epics:

- `[Roadmap][CEPIO v0.5 CONNECT] Live Industrial Integration`
- `[Roadmap][CEPIO v0.6 EXECUTE] Governed Industrial Outcomes`
- `[Roadmap][CEPIO v0.7 EXTEND] Industrial Developer Platform`
- `[Roadmap][CEPIO v0.8 OPERATE] Enterprise Runtime`
- `[Roadmap][CEPIO v0.9 GENERALIZE] Multi-Enterprise Portability`
- `[Roadmap][CEPIO v1.0 GUARANTEE] Production Guarantees`

Product-scoped work may use:

- `[CEPIO v0.5 CONNECT][P0] SAP live qualification`

Parallel components should retain component ownership rather than inherit a product label artificially:

- `[Runtime][P0] Kinetic trigger subscription`
- `[Lab][Drilling domain v0.4.1] Runtime qualification`
- `[Industry IQ][Reliability] ...`
- `[Backlog][P1] Purview governance and lineage bridge`

PR titles should retain conventional prefixes and name the actual capability/version owner, for example:

- `feat(retrieval): capability-routed Retrieval & Indexing v0.1`
- `feat(industry-iq): trusted catalogue v0.6`
- `feat(foundry): Reliability G1 hosted-agent qualification`

Do not rename a component to `v0.6` merely because it contributes to CEPIO v0.6 EXECUTE.

## Roadmap vs v1 scorecard

The product roadmap and the canonical v1 completion scorecard are intentionally separate systems.

### Roadmap

Answers:

> What proof must be completed before a CEPIO product release advances?

### v1 scorecard

Answers:

> How much evidence-backed CEPIO v1 maturity exists across the whole product?

The scorecard's dimension names are therefore **not product-release aliases**. Current scorecard dimensions include Foundation/Core, Platform Portability, Industry IQ, Assurance + Generalization, Enterprise Profiles + Native Deployment, Multi-Enterprise Portability and Production Guarantees.

Approximate conceptual relationship:

| Product roadmap | Scorecard dimensions that materially contribute |
| --- | --- |
| FOUNDATION | Foundation / Core |
| CONNECT | Platform Portability + integration evidence |
| EXECUTE | Industry IQ + operational/action assurance |
| EXTEND | Industry IQ + enterprise/profile/developer extensibility |
| OPERATE | Enterprise Profiles + Native Deployment + production operations evidence |
| GENERALIZE | Assurance + Generalization + Multi-Enterprise Portability |
| GUARANTEE | Production Guarantees plus completion of all critical prior evidence |

This relationship is intentionally many-to-many. Never silently rename scorecard dimensions to make them look identical to release labels.

The canonical score remains whatever `config/v1-scorecard.yaml` validates. New merges create possible evidence drift; they do not automatically change the score.

## Labels and milestones

Purpose, delivery status, product release and component version are separate concepts.

Use existing labels where available rather than creating overlapping aliases. A release milestone should be attached only where a product-release target is actually agreed. A component or Lab milestone must not be misrepresented as product release qualification.

Issue/PR history remains evidence and should not be rewritten merely to adopt newer terminology.

## Compatibility and evidence

This naming convention does not replace API, ontology, pack, application-contract or package compatibility policy.

For any material qualification claim, record:

- named capability/component;
- exact version;
- implementation/mainline evidence;
- qualification evidence;
- whether the evidence is synthetic/reference or real/live;
- whether the result changes a product release gate or only component maturity.

Preserve historical filenames, branches, tags and benchmark IDs unless a migration is explicitly required for repository correctness.

# API, SDK, Management and MCP

## Contract-first principle

CEPIO distinguishes its **industrial application contract** from the protocols used to access it.

The stable semantic/behavioral promise belongs to CEPIO contracts. REST, SDKs, MCP and Management are projections over those contracts; they must not invent independent industrial semantics or authority models.

```text
                   CEPIO industrial contracts
                            |
                    Application Contract
                            |
       +--------------------+--------------------+
       |                    |                    |
      REST                SDKs                  MCP
       |                    |                    |
 apps / services      Python / TypeScript   agents / Foundry

                 separate control-plane projection
                            |
                       Management
```

Current application envelope specification: [`application-contract-v0.2.md`](../application-contract-v0.2.md). Protocol convergence is documented in [`protocol-convergence-v0.3.md`](../protocol-convergence-v0.3.md).

## Current hosted surfaces

The hosted CEPIO target composition now exposes three deliberately separated surfaces:

```text
/api/v1/*          REST Application Contract
/management/v1/*   authenticated read-only Management projection
/mcp               authenticated Streamable HTTP MCP gateway
```

These surfaces share runtime contracts but not identical purpose/authority.

- `/api/v1/*` — application/runtime access;
- `/management/v1/*` — read-only runtime capability/health observation;
- `/mcp` — authenticated agent/tool protocol projection.

Management is not part of REST OpenAPI and must not become a remote administration bypass.

## Contract vs API

A CEPIO **contract** defines what a capability means, what evidence/authority it requires, what it returns and the invariants CEPIO guarantees.

An **API** defines one transport surface for using those capabilities.

```text
industrial semantic/runtime contracts
            |
      application contracts
            |
 REST / SDK / MCP / future events
```

OpenAPI remains an important compatibility artifact for REST, but OpenAPI is not the definition of CEPIO itself.

## Application Contract v0.2 execution kernel

The executable Skill path is protocol-neutral:

```text
SkillInvocation + trusted ExecutionContext
                |
                v
        actor-aware preflight
                |
            READY only
                |
                v
       executable Skill binding
                |
                v
       restricted governed host
                |
        +-------+-------+
        |               |
actor-scoped reads   authorized Functions
        |               |
        +-------+-------+
                |
                v
       SkillExecutionOutput
                |
         optional DecisionProposal
                |
                v
          SkillEvaluation
```

`SkillExecutorRegistry` binds stable Skill identity to executable procedure code while `SkillRegistry` remains authoritative for admission/readiness.

Executable Skills receive a restricted `SkillExecutionHost`, not raw runtime/source clients. A Skill may propose a Decision; the host persists it using trusted actor context. Skill capability does not automatically grant Action authority.

The maintenance-deferral reference Skill remains a bounded example of this separation.

## Protocol convergence

REST, Python SDK and MCP project the same Skill evaluation semantics through `CEPIOApplicationService`.

```text
                   SkillInvocation
                         |
          +--------------+--------------+
          |              |              |
        REST           Python SDK      MCP
          |              |              |
          +--------------+--------------+
                         |
              CEPIOApplicationService
                         |
                   evaluate_skill
                         |
                  SkillEvaluation
```

Cross-protocol conformance should preserve material Skill, evidence, recommendation, Decision and authority semantics even if generated IDs/timestamps differ.

## Public REST API v1

CEPIO exposes the versioned public application API under `/api/v1`.

Representative surface includes:

```text
/api/v1/health
/api/v1/objects
/api/v1/objects/{object_id}
/api/v1/query/objects
/api/v1/relationships
/api/v1/objects/{object_id}/neighbors
/api/v1/events
/api/v1/objects/{object_id}/events
/api/v1/skills/evaluate
/api/v1/functions/{name}
/api/v1/actions
/api/v1/decisions
/api/v1/decisions/{decision_id}
/api/v1/audit
/api/v1/graph/*
```

`openapi/cepio-v1.yaml` remains the accepted REST route/method/operation-ID compatibility baseline.

Dedicated state/provenance/schema REST resources should only be promoted when their independent public contract is intentionally stabilized; their absence from REST does not mean the runtime lacks those capabilities.

## REST security inheritance

REST uses authenticated host-derived actor context and inherits CEPIO runtime policy rather than implementing a parallel authorization model.

Controls include:

- actor-scoped object/property reads;
- query/graph restrictions;
- Function authorization;
- Skill preflight/execution;
- governed Decision persistence;
- Action policy/preconditions;
- immutable audit.

Caller-visible payloads do not permit caller-selected CEPIO identity/roles.

## Python and TypeScript SDKs

The Python and TypeScript clients are protocol conveniences over accepted CEPIO application operations.

They should remain thin:

- no embedded industrial procedure logic;
- no caller-selected authority semantics;
- no SDK-only business behavior unavailable through the application contract.

The SDK path already supports executable Skill evaluation through the REST projection.

Full supported-operation SDK coverage and developer-platform ergonomics remain part of v0.7 EXTEND qualification.

## MCP tool surface

The full CEPIO MCP server currently exposes eight governed tools:

```text
cepio_get_object
cepio_query_objects
cepio_get_state_at
cepio_explain_property
cepio_call_function
cepio_evaluate_skill
cepio_recommend_action
cepio_execute_action
```

The existence of `cepio_execute_action` in the full tool set does **not** confer execution authority. Normal actor policy, target constraints, preconditions, idempotency and audit remain authoritative.

`cepio_evaluate_skill` projects the same Skill invocation/evaluation contract used through REST/SDK.

## Hosted MCP gateway

Mainline now includes an authenticated Streamable HTTP MCP endpoint at `/mcp` in the hosted composition.

Security model:

```text
Entra / verified bearer identity
       |
       v
host authentication middleware
       |
       v
host-injected CEPIO actor context
       |
       v
MCP tool dispatch
       |
       v
normal CEPIO policy / Skill / Action runtime
```

Callers/models cannot submit their own CEPIO roles.

The hosted gateway also applies transport host/origin protections. Anonymous access is rejected before MCP protocol dispatch.

The Azure deployment workflow contains an explicit anonymous `/mcp` authentication smoke gate. A live deployment/environment qualification remains evidence that must be established by the corresponding deployment run rather than inferred from repository merge alone.

See [Foundry + MCP](../foundry-mcp.md) and ADR-0035.

## Least-privilege MCP profiles

Agent-host integrations can expose narrower tool profiles than the full eight-tool server.

The Reliability Foundry G1 qualification path uses a Decision-focused host profile that exposes governed reads, Functions and Skill evaluation while excluding Action execution tools.

This is stronger than a prompt instruction: the prohibited tools are absent from the host-exposed capability set.

For Microsoft-hosted agents:

> **Microsoft owns generic agent execution. CEPIO owns industrial agency.**

A merged qualification path does not equal a live Foundry PASS; real environment evidence is still required.

## Management Contract

Management is a separate control-plane contract and hosted read projection.

`/management/v1/*` is intended for runtime/Studio observation such as health and sanitized capability descriptors.

Important boundaries:

- authenticated;
- read-only;
- no policy mutation;
- no package installation/upgrade authority;
- no credentials/secrets/raw environment exposure;
- no direct source-system payload access;
- no bypass around Application Contract policy.

Browser/Studio experiences should normally use a trusted server-side/BFF pattern rather than hold broad CEPIO bearer tokens directly.

See [Management Control Plane](21-Management-Control-Plane.md) and [Remote Management Read Projection](../remote-management-read-projection.md).

## Recommendation vs execution

```text
Reasoning permission
      |
      v
recommend / persist Decision
      |
      +-- no execution authority -> stop / human approval
      |
      +-- execution authority -> Action policy + preconditions + audit
```

The same distinction applies regardless of REST, SDK, MCP or agent host.

## Evidence and model-output boundary

Protocol success does not itself prove industrial correctness.

```text
Model Output != Evidence
Tool Availability != Authority
Protocol Conformance != Operational Qualification
```

Agent answers/recommendations should be grounded in current-run authorized evidence, and higher-level assurance must separately test reasoning/Decision/outcome correctness.

## Current production-hardening gaps

Despite strong protocol productization, the public/application surfaces are not blanket production-GA.

Remaining work includes:

- deeper compatibility guarantees where required for v1.0;
- full SDK/CLI developer-platform coverage;
- public workflow-control surfaces where intentionally supported;
- cross-domain executable Skill qualification breadth;
- live Foundry Reliability G1 proof;
- live Copilot/Teams experience proof where required;
- enterprise SLO/HA/DR/security qualification;
- live SAP/PI CONNECT integration proof.

## Claim boundaries

- **v0.4 FOUNDATION:** public API/developer foundation qualified.
- **Hosted `/mcp`:** implemented in the authenticated hosted composition with deployment smoke requirements; live deployment evidence remains environment-specific.
- **Management:** implemented as authenticated read-only projection.
- **Foundry G1 path:** implemented; live G1 PASS is separate.
- **v0.5 CONNECT and later product releases:** not qualified merely by protocol implementation.

See [Current State](../current-state.md) and [Roadmap](17-Roadmap.md).

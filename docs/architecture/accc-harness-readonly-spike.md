# ACCC v0.1 — read-only composition candidate

Status: **draft, offline engineering qualification only**. No production route,
live-source attestation, paid inference, deployment or release qualification.

## Implementation and reuse

- ReadOnlyComposer reuses CapabilityRegistry and CapabilityRouter. It checks
  qualified maturity, validated domain, required capabilities, Skill readiness,
  evidence types and conflicts. It neither executes Skills nor authorizes Actions.
- AuthenticatedReadOnlyComposer binds existing ActorContext, CEPIORuntime read
  policy, SkillRegistry.preflight, EvidenceBinding and BindingRegistration. It
  checks identity and runtime permissions on every invocation, before source reads.
- The from_http_request factory calls existing get_actor_context for each invocation.
  Hosts must construct it per request with host-owned configuration and credentials.
  It adds no route and changes no authentication settings or permissions.
- CompositionRequest forbids extra fields: no tenant, actor, roles, approval,
  evidence facts, policy or Actions can be supplied through the tool schema.
- composition_tool is a lazy optional Microsoft Agent Framework FunctionTool
  adapter. The composition host remains provider-neutral. No model client, shell,
  file, web, Skill execution or generic Harness tool is installed.

## Host configuration and fail-closed limits

AdmissionProfile is trusted host configuration, never a request body. It pins
one tenant/subject/domain, a policy version, exact capability/Skill contract hashes,
an explicit compatible capability set and bounded external evidence records.
Host qualification must justify these pins; a hash does not independently qualify
a Skill or method. Unknown combinations and changed contracts are blocked.

The host uses existing function authorization for cepio.compose_readonly, object
sharing/type policy for the target and read-type policy for each evidence type.
An unconfigured reference RolePolicyEngine is rejected.
No production permission is added by this PR. Nonempty capability policy
requirements are unsupported and blocked. Action-bearing and Decision-producing
Skills are rejected even if an actor could otherwise execute them.

Evidence must come from a ready, versioned, read-only registered binding. The adapter
payload convention contains tenant, subject, evidence type, observed time, explicit
conflict state and payload hash. Source identity/version/scope/time are checked.
Missing or stale evidence cannot satisfy an evidence type; conflicts block.
This is a host binding contract, **not cryptographic source attestation**. A trusted
source adapter is responsible for truthful conflict state and payload hashes.

Receipts bind actor/roles digest, tenant, policy version, binding, evaluation time,
capability and Skill definitions, and source envelope hashes. The manifest additionally
binds request text, subject, domain, selected capabilities and their versions.
The same frozen inputs and clock reproduce the same receipt. These hashes are not
signatures or authorization tokens. Re-evaluate admission before any later use.
Blocked responses contain no admitted Skills or capabilities.

The existing Entra validator checks signatures, audience, issuer, tenant and expiry.
This adapter does not add token introspection or immediate identity-provider session
revocation. Runtime policy revocation is checked on each call.

## Optional Microsoft integration

Install agent-framework-core==1.24.0 separately for the tested SDK boundary.
Then call composition_tool(request_scoped_host) and supply only that tool to the
embedding agent. Approval mode remains always_require; the adapter does not grant
auto-approval. The embedding host must preserve its authorization and approval path.

The optional create_readonly_harness factory uses the actual SDK Harness with only
the ACCC tool. Web search, file memory, todo, mode and compaction providers are disabled;
no shell, file-access, Skill discovery or background agents are configured. Tests
exercise the real Harness with a scripted offline client: no source read before approval,
no source read after denial or policy revocation, and one read after approved admission.
This qualifies offline SDK mechanics, **not live-model or production-host behavior**.
Reference: [Microsoft function tools](https://learn.microsoft.com/en-us/agent-framework/agents/tools/function-tools).

## Reproduce

```sh
python -m pip install -e '.[dev]' -r requirements-quality.txt
python -m pip install agent-framework-core==1.24.0
python -m pytest -q tests/test_accc*
PYTHONHASHSEED=1 python examples/accc_k201_offline.py > /tmp/accc-1.json
PYTHONHASHSEED=7 python examples/accc_k201_offline.py > /tmp/accc-7.json
cmp /tmp/accc-1.json /tmp/accc-7.json
```

The K-201 fixture uses synthetic identifiers and no industrial measurements,
proprietary thresholds or domain reasoning. It demonstrates READY and safe abstention
only. It does not demonstrate independent Industry IQ uplift or v0.5 CONNECT.

## Review gates

Review the host configuration/identity lifetime, evidence adapter convention and
unsupported-policy fail-closed behavior. Require CI, Governance, CodeQL and Quality
Gate on the final head before merge. Architecture decision: ADR-0055 (proposed).
CEPIO-Labs IP, canonical scorecard and release gates remain unchanged.

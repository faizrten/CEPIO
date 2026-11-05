# Professional work context — read-only v0.1

Status: host-local implementation candidate. No hosted endpoint, persistence
adapter, Studio screen, operational authorization or field qualification is added.
This is the first bounded WC-02 slice following the work-cycle plan in PR #342.

## Professional purpose

Represent a customer's own problem across understand, assess, work and learn.
Each stage can contain relevant professional questions. The projection identifies
whether the host's admitted capability has the evidence needed to begin an
assessment. It does not generate the answer or establish engineering correctness.
There are no scenario-specific IDs or Rig 07 branches.

## Contracts and ownership

`WorkContextRequest` accepts only a work ID and expected revision. Extra fields,
including actor, tenant, roles and approval assertions, are rejected.

`WorkContextHost` supplies an existing `HostPrincipal` and a freshly authorized
`WorkSnapshot`. The host must enforce current actor/property/source permissions
for **every** reference and field, recheck revoked rights, verify source versions,
evaluate applicability/conflicts, and determine capability admission through
existing registries/preflight. It must supply bounded selected evidence IDs and
an authoritative revision that changes when relevant context changes.

`read_work_context` is a host-only projection helper, not a security gateway.
Do not deserialize a client-provided snapshot, expose host methods as agent
arguments, or treat constructing a HostPrincipal as authentication. The caller
supplies the trusted current evaluation time. No authentication/permission control
is changed. A real adapter remains to be implemented and qualified.

The projection checks work/tenant correspondence and expected revision; denies
mismatched scope; and returns explicit blockers for absent, expired, future,
inapplicable, conflicting or unselected required evidence. All required evidence
must survive context selection. The existing ContextAssembler is unchanged.

Evidence receipts preserve source identity/version and validity; references to
subjects, Decisions and outcomes remain references to existing contracts. No new
canonical ontology class, source of truth, runtime or database is introduced.

## Distinct meanings

| Field | Meaning |
| --- | --- |
| capability_admission | Host-reported ready, blocked or unknown capability admission |
| evidence_completeness | Whether all declared evidence passed these bounded checks |
| assistance_state | Ready for assessment, or unresolved; never an approved answer |
| job_readiness | Always not_assessed in this version |
| action_authority | Always not_granted in this version |

An empty question list is allowed and asserts no completed process. A question
requires at least one evidence reference; evidence-free clarification and justified
not-applicable states are future extensions. Source correctness, dependency impact,
procedure applicability, numerical reasoning and actual authorization are not
established merely by these schemas or local tests.

## Verification

Run:

```bash
python -m pytest -q tests/test_work_context.py tests/test_memory_context.py tests/test_accc_host_admission.py --cov=cepio.work_context --cov-report=term-missing
ruff check src/cepio/work_context.py tests/test_work_context.py
ruff format --check src/cepio/work_context.py tests/test_work_context.py
```

Local result on Python 3.12: 44 tests passed; the new module had 100% statement
coverage. Tests cover all stages, missing/dropped evidence, stale/future evidence,
conflicts, applicability, blocked/unknown capabilities, work/tenant mismatch,
revision changes, host denial after resume, missing identity, authority-field
injection, invalid dates, duplicate evidence IDs and no snapshot mutation.

Host tests use synthetic trusted-service doubles. These results do not qualify
live authorization, persistence, whole-repository CI or production deployment.

## Next integration gate

Implement an adapter to authorized existing work/evidence sources, bind revisions
to source changes, then expose the projection in an isolated four-stage Studio
preview. Persisted continuity and concurrent writes remain separate WC-02 work;
question routing, substantive assistance and change propagation remain WC-03/05.
Preserve the existing production and source-verification gates.

## Summary

## Risk classification

- [ ] low
- [ ] medium
- [ ] high

## Governance changes

For protected paths, explain why the controls remain effective, identify the ADR,
and describe validation. Otherwise write N/A with a reason.

- [ ] Existing gates remain enforced.

Describe the change and why it is needed.

## Linked issue

Use one of:

- `Closes #<issue>`
- `Fixes #<issue>`
- `Refs #<issue>`
- `N/A — <reason>` for narrowly scoped maintenance where an issue would add no governance value.

> 

## Change class

Select at least one:

- [ ] Runtime / execution
- [ ] Public API / SDK / MCP
- [ ] Canonical ontology / semantics
- [ ] Profile / customer extension
- [ ] Source adapter / integration
- [ ] Generalization / competency harness
- [ ] Security / policy / governance
- [ ] Deployment / operations
- [ ] Documentation only
- [ ] Maintenance / refactor

## Architecture / semantic impact

- [ ] This change preserves CEPIO's source-system-neutral core boundary.
- [ ] Source/customer-specific semantics remain in adapters, mappings, profiles or fixtures unless reuse evidence justifies canonical promotion.
- [ ] Agents/applications cannot bypass CEPIO identity, policy, Action Runtime, workflow governance or audit.
- [ ] External side effects, if any, use governed Action/adapter/writeback paths and verification/reconciliation semantics.
- [ ] No canonical CEPIO concept is introduced solely to mirror a source-system field or customer-specific term.

Describe any architecture invariant affected, canonical semantic promotion, or deliberate exception:

> 

## Validation

- [ ] Relevant tests pass.
- [ ] Ontology / compatibility / SHACL checks pass when applicable.
- [ ] Public API/client contract checks pass when applicable.
- [ ] Reference examples, fixtures or demos were updated when applicable.
- [ ] New or changed behavior has a deterministic regression test where practical.

## IP / publication review

Every material change to the public CEPIO repository must be classified before merge.

Choose one:

- [ ] **PUBLIC** — publication improves adoption, interoperability, validation or trust without unnecessarily exposing differentiated CEPIO implementation or industry intelligence.
- [ ] **PROTECTED — public abstraction only** — the underlying capability remains private; this PR exposes only the deliberate interface, abstraction, specification or sanitized example.
- [ ] **CUSTOMER CONFIDENTIAL — publication prohibited** — this PR contains customer-derived or otherwise confidential material and must not be merged into the public repository.

For `PUBLIC` or `PROTECTED — public abstraction only`, confirm:

- [ ] No customer-confidential data, mappings, thresholds, procedures, policies, models or learned behaviour are included.
- [ ] No protected benchmark/evaluation corpus or proprietary industrial reasoning is included unless publication is explicitly intentional.
- [ ] I considered whether the same ecosystem value could be achieved with a narrower interface, abstraction or sanitized example.
- [ ] Publication value exceeds replication/IP-exposure risk.

If `PROTECTED — public abstraction only`, state what remains private and why this public surface is safe to publish:

> 

See [`docs/governance/ip-publication-policy.md`](../docs/governance/ip-publication-policy.md).

## Documentation impact

Documentation is part of CEPIO's definition of done.

Choose one:

- [ ] **Documentation updated** — I updated the relevant focused technical docs and/or `docs/wiki/` pages in this PR.
- [ ] **No documentation impact** — this change does not alter user-visible or developer-visible behavior, architecture, semantics, interfaces, integrations, deployment, security, governance, examples, release status, or roadmap state.

If selecting **No documentation impact**, explain why:

> 

### Documentation areas to consider

- ontology modules, classes, properties, relationships, profiles
- REST API, Python SDK, CLI, MCP, query contracts
- runtime, persistence, temporal/provenance, functions/actions/policy
- Fabric, Foundry, Entra, NVIDIA or other platform integrations
- SAP, AVEVA PI, OSDU, P6 or other source adapters
- deployment, security, governance and observability
- migration/versioning/compatibility contracts
- standards federation
- examples, reference scenarios, roadmap and release status

## Breaking changes / migration

- [ ] No breaking semantic or interface change.
- [ ] Breaking change is covered by the required migration/versioning contract.

If breaking, identify the migration/version boundary and compatibility evidence:

> 

## Release / product claim impact

State whether this PR changes a CEPIO release gate, roadmap status or product claim. If none, write `None`.

> 

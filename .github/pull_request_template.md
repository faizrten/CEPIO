## Summary

Describe the change and why it is needed.

## Validation

- [ ] Relevant tests pass.
- [ ] Ontology / compatibility / SHACL checks pass when applicable.
- [ ] Reference examples or demos were updated when applicable.

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

# CEPIO v0.2 Release Manifest

Release: **0.2.0 — Operational Kernel**

## Verified locally

- 15 pytest tests pass.
- All Turtle ontology modules parse.
- RDF type registry loads subclasses and relationship constraints.
- Reference SHACL graph conforms using the offline CEPIO bootstrap validator.
- Cross-domain refinery demo executes end-to-end.
- SQLite object persistence survives runtime restart.
- Optimistic concurrency rejects stale object versions.
- Every governed action attempt writes an audit record.
- Idempotent retry does not duplicate a work order.
- Authorization is evaluated before idempotent replay.
- AI recommender role cannot execute governed maintenance actions.
- Agent read path filters sensitive properties in the reference policy.
- Integration adapters are dry-run only.

## Release acceptance scenario

`Hydrocracker Margin KPI → Hydrocracker → K-201 compressor → trip events → risk/production-loss functions → Decision → governed CreateWorkOrder → critical spare → supplier → immutable audit`

## Known limits

- SQLite is a reference backend, not a production distributed graph store.
- Full pySHACL is configured in the dev/CI dependency set; the restricted build environment used for this release could not download new packages, so local validation used CEPIO's bootstrap SHACL subset validator.
- Adapter implementations perform no production side effects.
- MCP is provided as a governed facade; a production MCP transport/server is a later milestone.
- Compensation is represented and surfaced by the action runtime but automated rollback orchestration is not yet implemented.

## Next release

v0.3 targets temporal history, provenance/lineage, event-to-state projections, ontology migration compatibility, richer query contracts and runtime observability.

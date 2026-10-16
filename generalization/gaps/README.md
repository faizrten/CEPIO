# Gap triage

Gap triage records the architecture decision taken after a frozen Generalization Harness competency exposes missing semantics.

A triage artifact is not part of the frozen challenge batch. It is the controlled response to that batch against a specific ontology state.

Each missing semantic receives exactly one disposition:

- `CORE` — reusable canonical semantics across Energy & Process Industry archetypes;
- `DOMAIN` — canonical domain specialization;
- `PROFILE` — customer/fleet/deployment-specific semantics;
- `MAPPING` — external taxonomy/codeset/source vocabulary to federate rather than copy;
- `REJECT` — the literal missing term or edge is the wrong abstraction.

`REJECT` may include a `replacement_layer` when the business need is valid but should be satisfied by another abstraction.

Accepted triage is executable: the harness rejects untriaged current gaps, duplicate coverage, unknown references and stale entries. Semantic remediation must therefore update the corresponding triage record in the same change.

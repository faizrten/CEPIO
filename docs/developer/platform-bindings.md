# Platform bindings

CEPIO platform bindings are deliberately thin. They connect authoritative external systems to the stable CEPIO operating contract without moving provider schemas or industrial reasoning into Core.

## Choose the boundary first

| Concern | Owner |
| --- | --- |
| identity, provenance, policy, Decision/Action contracts | CEPIO Core |
| failure modes, operating constraints, decision patterns, Skills | Industry IQ |
| provider transport and translation | Platform binding |
| experimental evaluators/model-specific qualification | CEPIO Labs |

A platform binding must not become a generic integration platform. Prefer native platform access and preserve authoritative source identity.

## Binding modes

### Evidence

Use an `evidence` binding when CEPIO needs authoritative observations/context without a side effect. Evidence returns normalized data with an `ExternalRecordReference` so source system, record identity and record version remain explicit.

Evidence bindings cannot declare governed-write, verify or reconcile capabilities. If the source offers a meaningful version/etag/revision, declare `versioned-identity` and preserve it in `record_version`.

Typical v0.5 consumers: Fabric and Cognite. OSDU/ADME continues to use the existing REUSE/BIND federation boundary.

### Governed action

Use a `governed-action` binding for source-authoritative side effects. The implementation must satisfy the existing `GovernedWriteAdapter` contract and be invoked through CEPIO Action Runtime. It must preserve idempotency and keep verification/reconciliation explicit.

SAP work-management writeback is the first intended v0.5 consumer. Do not introduce a second write runtime or a direct agent-to-provider path.

## Scaffold

```bash
python scripts/scaffold_binding.py \
  --binding-id fabric-observation \
  --provider-id microsoft.fabric \
  --source-system fabric \
  --mode evidence \
  --output /tmp/fabric-observation
```

For governed writeback:

```bash
python scripts/scaffold_binding.py \
  --binding-id sap-work-management \
  --provider-id sap.s4hana \
  --source-system sap_s4hana_eam \
  --mode governed-action \
  --output /tmp/sap-work-management
```

The scaffold creates `binding.yaml`, `binding.py` and a boundary checklist. Generated implementations fail closed until provider transport is supplied.

## Conformance

`cepio.platform_bindings` keeps write qualification behind the existing governed runtime:

- `qualify_evidence_binding` checks declared capability, source identity, record identity, optional version provenance and absence of a write surface;
- `qualify_governed_action_adapter` checks the adapter declaration/shape without dispatching anything;
- `qualify_governed_action_execution` exercises idempotent dispatch plus either verification or reconciliation **through `ExternalActionRuntime` only**.

No conformance helper calls an adapter write method directly. The architecture invariant that external dispatch is confined to `external_actions.py` remains unchanged.

These checks complement provider/domain tests; they do not replace them. Domain-specific evidence APIs such as Petrophysics remain domain-owned until multiple independent use cases justify a reusable Core abstraction.

## North-Star rule

When adding a binding, ask: **could the same Industry IQ Skill run when this provider is replaced?** If not, provider behavior has probably leaked into the industrial-intelligence layer.

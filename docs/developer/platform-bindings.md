# Platform bindings — Binding Contract v0.1

CEPIO platform bindings are deliberately thin. They connect authoritative external systems to the stable CEPIO operating contract without moving provider schemas or industrial reasoning into Core.

The durable product boundary is the **Binding Contract**. Provider adapters may change; the contract consumed by CEPIO Runtime, Management and Industry IQ must not.

## Contract layers

```text
Provider implementation
        │
        ▼
PlatformBindingManifest
what the implementation guarantees
        │
        ▼
BindingRegistration
what the host intentionally configures/exposes now
        │
        ├──────────────► Management BindingDescriptor
        │                 Studio/runtime inventory
        ▼
Evidence / governed-action conformance
        │
        ▼
Industry IQ Skill
```

This separation prevents three concepts from being conflated:

1. **provider support exists in the repository**;
2. **a binding implementation satisfies the CEPIO contract**;
3. **a binding is intentionally registered/configured in one runtime**.

Only the third creates management-plane binding inventory.

## Choose the boundary first

| Concern | Owner |
| --- | --- |
| identity, provenance, policy, Decision/Action contracts | CEPIO Core |
| failure modes, operating constraints, decision patterns, Skills | Industry IQ |
| provider transport and translation | Platform binding |
| runtime binding registration/status | Binding Contract |
| operator/admin inventory projection | Management Contract |
| experimental evaluators/model-specific qualification | CEPIO Labs |

A platform binding must not become a generic integration platform. Prefer native platform access and preserve authoritative source identity.

## Binding manifest

`PlatformBindingManifest` is the invariant declaration embedded by a binding implementation. It defines:

- binding identity;
- provider identity;
- authoritative source-system identity;
- binding mode;
- declared capabilities;
- Binding Contract schema version.

The manifest is independent of runtime health/configuration state.

## Binding registration

`BindingRegistration` is an explicit host/runtime declaration. It combines a manifest with:

- an industrial `capability_id`;
- runtime status: `ready`, `degraded` or `not-configured`;
- derived access mode;
- derived authority semantics;
- the Binding Contract version.

Use `register_evidence_binding(...)` or `register_governed_action_binding(...)` to create registrations through the contract boundary.

Management derives `BindingDescriptor` from the registration rather than independently re-declaring provider, access mode or authority. Legacy direct descriptors remain supported only for compatibility.

## Binding modes

### Evidence

Use an `evidence` binding when CEPIO needs authoritative observations/context without a side effect. Evidence returns normalized data with an `ExternalRecordReference` so source system, record identity and record version remain explicit.

Evidence bindings cannot declare governed-write, verify or reconcile capabilities. If the source offers a meaningful version/etag/revision, declare `versioned-identity` and preserve it in `record_version`.

Typical consumers: Synthetic reference providers, Microsoft Fabric and Cognite. OSDU/ADME continues to use the existing REUSE/BIND federation boundary until a concrete provider binding is required.

Evidence registrations derive:

```text
access mode = read
authority   = observation-only
```

### Governed action

Use a `governed-action` binding for source-authoritative side effects. The implementation must satisfy the existing `GovernedWriteAdapter` contract and be invoked through CEPIO Action Runtime. It must preserve idempotency and keep verification/reconciliation explicit.

SAP work-management writeback is the first intended consumer. Do not introduce a second write runtime or a direct agent-to-provider path.

Governed-action registrations derive:

```text
access mode = write
authority   = governed-action
```

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

- `register_evidence_binding` validates the evidence-binding shape without reading customer/source data;
- `register_governed_action_binding` validates governed adapter shape without dispatching a write;
- `qualify_evidence_binding` checks declared capability, source identity, record identity, optional version provenance and absence of a write surface;
- `qualify_governed_action_adapter` checks the adapter declaration/shape without dispatching anything;
- `qualify_governed_action_execution` exercises idempotent dispatch plus either verification or reconciliation **through `ExternalActionRuntime` only**.

No conformance helper calls an adapter write method directly. The architecture invariant that external dispatch is confined to `external_actions.py` remains unchanged.

These checks complement provider/domain tests; they do not replace them. Domain-specific evidence APIs such as Petrophysics remain domain-owned until multiple independent use cases justify a reusable Core abstraction.

## Portability proof

The current drilling NPT proof deliberately runs the same Industry IQ against both:

```text
SyntheticDrillingNPTBinding
           │
           ├── Binding Contract v0.1
           │
FabricDrillingNPTBinding
           │
           ▼
      same NPT Skill
           │
           ▼
semantically equivalent assessment
```

Provider/source provenance remains different; industrial interpretation remains equivalent.

## North-Star rule

When adding a binding, ask: **could the same Industry IQ Skill run when this provider is replaced?** If not, provider behavior has probably leaked into the industrial-intelligence layer.


## Provenance and external writeback safety qualification

A canonical property mutation that supplies `PropertyProvenance` must validate the source object's identity and canonical property IRI, and confirm that a provenance repository exists, **before** mutating the CEPIO object. The authenticated MCP explanation path also checks object/property read authorization before exposing the provenance source. This is a validation-order invariant, not a claim that the reference storage layer supports an atomic distributed transaction across source system and provenance store.

External writeback outcomes must remain queryable and restart-safe. A transport failure after dispatch produces an **unknown** state, not permission to write again. Even after process restart, `dispatch` and `verify` cannot blindly retry an unknown outcome. Only explicit source reconciliation may resolve the record to verified/failed, preserving the original action, actor, decision and correlation identity. Offline fake-adapter tests prove these runtime invariants; real SAP read-back and live CONNECT qualification remain open under #53/#57/#58.

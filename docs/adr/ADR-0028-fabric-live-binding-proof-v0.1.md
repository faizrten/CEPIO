# ADR-0028 — Microsoft Fabric Live Binding Proof v0.1

**Status:** Proposed

## Context

Binding Contract v0.1 established the provider-neutral boundary between CEPIO Industry IQ and authoritative industrial platforms. Synthetic and Microsoft Fabric drilling NPT bindings already pass the same offline semantic parity qualification, but the Fabric side still uses an injected in-memory table reader in repository tests.

The next proof must establish that the same binding contract and the same Industry IQ can consume rows from an actual Microsoft Fabric data item without moving Fabric transport, authentication or workspace semantics into CEPIO Core.

Microsoft Fabric Warehouse and SQL analytics endpoints expose TDS/SQL connectivity with Microsoft Entra authentication. This provides a stable read surface that does not require CEPIO to depend on Fabric preview ontology item-definition APIs.

## Decision

Adopt a **live, read-only Fabric SQL proof path** under `cepio.integrations.microsoft`.

### 1. Keep the existing domain binding unchanged

`FabricDrillingNPTBinding` remains the owner of Fabric-row to CEPIO drilling-evidence translation. The new transport implements only its existing `FabricDrillingNPTTableReader` seam.

```text
Fabric Warehouse / SQL analytics endpoint
             |
       Entra-authenticated SQL
             |
     FabricSqlTableReader
             |
   FabricDrillingNPTBinding
             |
      Binding Contract v0.1
             |
       Drilling NPT IQ
```

No Fabric transport dependency is introduced into CEPIO Core or the Drilling NPT Industry IQ pack.

### 2. Use Microsoft Entra authentication only

The first proof supports `ActiveDirectoryDefault` for local Azure CLI/federated CI, `ActiveDirectoryMSI` for Azure-hosted CEPIO, and explicit interactive/device-code developer modes. The CEPIO settings model does not accept username/password/client-secret fields.

### 3. Use only fixed reviewed proof statements

`FabricSqlTableReader` accepts an explicit subset of the three v0.1 proof tables, but schema names, table names and SQL text are not runtime-configurable. Each supported table maps to a fixed reviewed `SELECT` statement against the dedicated `cepio_proof` schema. The only runtime SQL value is the parameterized `context_id`. The reader exposes no mutation method.

This intentionally gives up generic SQL-table access in v0.1 in favor of a narrow, auditable proof boundary.

### 4. Keep the first proof synthetic-only

The checked-in Fabric bootstrap SQL creates a dedicated `cepio_proof` schema and one synthetic drilling context. It contains no customer data. The live proof compares Fabric-backed evidence to a checked-in synthetic semantic control and requires the same semantic signature and NPT assessment while allowing provider provenance to differ.

### 5. Make live qualification explicitly opt-in

Ordinary CEPIO CI remains credential-free and deterministic. The live proof can be run locally or through the manually triggered `CEPIO Fabric Live Binding Proof` GitHub workflow. The workflow runs only when `FABRIC_LIVE_PROOF_ENABLED=true` and uses the `dev` environment Azure OIDC identity, which must separately receive least-privilege access to the Fabric proof item.

## Security boundary

The proof must not contain Fabric credentials in source control, expose customer data, grant the evidence binding write authority, infer connectivity merely because provider code exists, accept runtime-supplied SQL identifiers/statements, or bypass Binding Contract/Industry IQ qualification.

## Validation

Repository acceptance requires unit tests for fixed allow-listed parameterized SQL, resource closure, secretless configuration, fail-closed missing/unsafe configuration, optional-driver failure, semantic-drift failure, and preservation of the existing offline Synthetic/Fabric parity. Full CEPIO CI, Quality, compatibility, governance and CodeQL gates remain required.

A **live proof PASS** is a separate environment qualification and is only established when the manual/local proof reaches a configured Fabric item.

## Consequences

CEPIO gains a concrete path from real Fabric rows to the same Industry IQ used by the Synthetic provider while Fabric remains replaceable. The first live proof targets SQL/TDS only; workspace/item provisioning remains external to CEPIO.

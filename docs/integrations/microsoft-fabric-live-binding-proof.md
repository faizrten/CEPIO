# Microsoft Fabric Live Binding Proof v0.1

This proof demonstrates a stronger claim than the offline Fabric adapter tests:

> The same CEPIO Drilling NPT Industry IQ produces the same semantic result when its evidence comes from a real Microsoft Fabric SQL endpoint rather than the Synthetic provider.

It uses only synthetic reference data. No customer data is required.

## Proof chain

```text
Synthetic reference JSON                 Fabric Warehouse / SQL endpoint
          |                                          |
SyntheticDrillingNPTBinding                     Entra SQL
          |                                          |
          |                                  FabricSqlTableReader
          |                                          |
          |                                  FabricDrillingNPTBinding
          |                                          |
          +------------ Binding Contract v0.1 -------+
                             |
                     same Drilling NPT IQ
                             |
                    same semantic signature
                             |
                          PASS/FAIL
```

## 1. Prepare a Fabric proof item

Create or reuse a **non-production Fabric Warehouse** for the proof. In its SQL query editor, run `examples/fabric/drilling-npt/bootstrap.sql`. The script creates only the dedicated `cepio_proof` schema and synthetic `NPT-CONTEXT-001` rows.

For runtime access, use least privilege. The CEPIO identity needs read access to the Fabric item and `SELECT` access to the proof tables; it does not need CEPIO write authority.

The v0.1 reader deliberately fixes the schema and supported table statements in code. Runtime configuration cannot supply a schema, table name or SQL statement. The only SQL value supplied at runtime is the parameterized `context_id`.

## 2. Get the Fabric SQL endpoint

From the Fabric Warehouse / SQL analytics endpoint settings, copy the SQL connection details and retain only the server and database/item database name. Do not commit a connection string or credential.

## 3. Run locally

```bash
python -m pip install -e '.[fabric-sql]'
az login
export CEPIO_FABRIC_SQL_SERVER='<fabric-sql-server>'
export CEPIO_FABRIC_SQL_DATABASE='<database-name>'
export CEPIO_FABRIC_SQL_AUTH='ActiveDirectoryDefault'
export CEPIO_FABRIC_DATASET_ID='cepio-fabric-live-proof'
python scripts/qualify_fabric_drilling_npt_live.py
```

A successful result includes the Binding Contract version, Fabric provider identity, semantic signature, NPT hours and evidence-reference count. It excludes connection credentials and raw Fabric payloads.

## 4. Run from GitHub Actions

The workflow `.github/workflows/fabric-live-proof.yml` is manual-only and uses the existing `dev` environment OIDC identity.

Configure `dev` environment variables:

```text
FABRIC_LIVE_PROOF_ENABLED=true
CEPIO_FABRIC_SQL_SERVER=<fabric-sql-server>
CEPIO_FABRIC_SQL_DATABASE=<database-name>
CEPIO_FABRIC_DATASET_ID=cepio-fabric-live-proof
```

The existing Azure OIDC secrets `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and `AZURE_SUBSCRIPTION_ID` are also required. Grant that service principal the minimum Fabric access needed for the proof. Fabric tenant policy must permit service-principal access where required.

Run **Actions → CEPIO Fabric Live Binding Proof → Run workflow**.

## PASS criteria

The run passes only if the Fabric SQL connection authenticates with Microsoft Entra, the fixed allow-listed proof tables resolve the complete evidence context, every evidence reference retains source identity/version, Binding Contract registration succeeds, and Fabric/Synthetic produce identical semantic signatures and NPT assessments.

Provider provenance must remain different. That difference proves the data platform changed while the industrial interpretation did not.

## What this does not prove

This v0.1 proof does not establish production Fabric connectivity, customer-data onboarding, Eventhouse/KQL support, Fabric Ontology deployment, writeback or bounded autonomy. Those remain separate capability gates.

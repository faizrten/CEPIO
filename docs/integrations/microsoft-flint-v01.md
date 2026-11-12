# Microsoft Flint evaluation in CEPIO: M0–M2

Status: **evaluation only, synthetic development; no production permission, customer tenant, new public API, Azure provisioning, or paid inference**.

## M0: Dependency qualification

Upstream: [microsoft/flint-chart](https://github.com/microsoft/flint-chart), MIT-licensed, version `flint-chart@1.0.1` (exact direct evaluation pin, Node >=20). This is **Flint**, not full Data Formulator. The source and MIT license are public and available. The [OSS dependency register](../governance/oss-dependency-register.json) records the workstream as `evaluation`, never production-approved.

Security and sustainability: current upstream documentation supports `validateChart` and `assembleVegaLite`; maintainer support is not guaranteed. CEPIO keeps a portable Vega-Lite fallback; disabling Flint must not destroy evidence, chart intent or decisions. The isolated evaluation workflow runs `npm audit --omit=dev --audit-level=high` with no secrets. The package is not installed into CEPIO Python Core. A production decision still requires transitive dependency lock/SBOM, license/notice review, renderer isolation, accessibility, CSP, source permission tests, and approved fallback migration.

Do not use the public hosted Flint MCP endpoint for private case data. Future MCP uses must disable local file references and enforce tenant-scoped egress rules.

## M1: Synthetic K-201 evidence charts

`examples/flint_k201_synthetic.json` has **invented** dated readings for vibration RMS (mm/s), bearing temperature (degC), and operating load (%). They are deliberately separate charts, not a misleading dual-unit plot. The fixture is neither historian evidence nor a diagnosed mechanical cause; fixture SHA hashes are not enterprise signatures.

Generate three host-owned visualization envelopes:

```bash
PYTHONPATH=src python examples/flint_k201_offline.py --out-dir /tmp/cepio-flint-envelopes
```

Run the real pinned Flint compiler in an **isolated** Node test directory:

```bash
cd experiments/flint
npm install --ignore-scripts --no-fund
npm audit --omit=dev --audit-level=high
node compile.mjs /tmp/cepio-flint-envelopes /tmp/cepio-flint-compiled
```

Each Flint result contains a native Vega-Lite spec, its compiler identifier, CEPIO source/value hashes and interaction intent. It has to pass `validateChart` and `assembleVegaLite`; no fallback can pretend to be a successful Flint run. The `flint-evaluation.yml` workflow performs this on the synthetic PR and retains the artifacts for 7 days. The declared `inspect-index` and `brush-x` interactions are for an eventual compatible UI; no interactive Studio is deployed in M0–M2.

## M2: CEPIO-owned, portable contract

`src/cepio/visualization_contract.py` provides host-only `build_readonly_visualization`, producing a `cepio.visualization/0.1` envelope. The host, not the user or LLM, binds tenant, actor and evidence authorization; permission is checked for every record per call. Envelopes include source/version/hash references and deterministic data/provenance SHA256 hashes.

The Flint compiler receives only `flint_input` containing inline, authorized data and semantic chart intent—never case credentials, actor, tenant ID or full evidence ledger. The same envelope also preserves a CEPIO-generated `fallback_vegalite` spec independently of Flint. Bounded validation rejects invalid/nonfinite numbers, naive or duplicate timestamps, and oversized series. There is **no HTTP route or hosted MCP tool** in this increment.

Generic interface, not K-201 hard-coded: different industrial cases may use the same visualization contract after the host provides genuinely versioned, authorized and independently verified evidence. A chart never claims causality, intervention approval or improved judgment.

## Reproduce and qualify

```bash
python -m pytest -q tests/test_visualization_contract.py
```

The tests check deterministic hashes, permission revocation, wrong tenant, partial denial, invalid evidence, timestamp ordering, nonfinite values, safe Flint input, and three independent unit-separated signal charts.

**Remaining before production:** lock transitive npm dependencies; independent license/security/adversarial review; verifiable tenant evidence source; renderer sandbox/CSP, no remote file references, authorization and decision contract tests, and a tested UI fallback. M3 (Studio and no second login) is not included.

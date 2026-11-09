# Cognite Open Industrial Data — CEPIO M0 evidence inventory (read-only)

**Status:** Implementation and offline tests only until an authorized user runs the live probe. This is not live-qualified integration and must not appear as \`ready\` in Studio or CEPIO Management until runtime registration, identity/permission validation and a verified source probe have separately passed.

## Goal

Establish a frozen, reproducible *metadata* inventory of Cognite Open Industrial Data (OID), discover compressor-related assets, and prove one CDF record can resolve through CEPIO Binding Contract v0.1 with original CDF numeric identity, \`lastUpdatedTime\` source version and data-project provenance. The provider owns facts; CEPIO owns reusable operating meaning. This step deliberately does **not** assess diagnosis, prediction or operating value.

## Scope and safeguards

- Only Cognite OID projects \`publicdata\` / \`publicdatacdm\` on \`https://api.cognitedata.com\` are permitted; start with \`publicdata\`.
- Uses only SDK \`list\`, \`search\` and \`retrieve\` of *metadata* for assets, time series, events and files. No datapoints, file downloads, writes, external actions, bulk enumeration or Azure provisioning.
- 100 results maximum per resource by default (hard cap 200), 20 compressor name-search results by default (cap 100), relationships for at most 10 matched assets. Counts are explicitly **sample counts, not total project counts**.
- Asset-name fuzzy search is candidate discovery only; it is not ground truth for compressor scope, equipment relationships, decision outcomes or completeness. Empty search returns zero candidates, not an inferred asset.
- \`lastUpdatedTime\` is a source metadata revision timestamp, **not** an operating observation time, proof of first/last datapoint, or a complete immutable historical source snapshot. A new metadata revision invalidates prior conformance assumptions; full decision reproducibility will require frozen time-window evidence and data hashes in M1.
- Fail closed when asset identity, project, host, timestamp version or required API capabilities are missing. No arbitrary credentials, source-response dumps or tokens appear in the report.
- SHA-256 fingerprint covers only the compact inventory manifest. It is reproducible for the same returned samples; not a cryptographic signature, source attestation or digest of all underlying source data.
- The binding declares \`resolve-evidence\` and \`versioned-identity\` only. No write, verification or reconciliation capability. The probe validates a candidate locally but does **not** register it in the CEPIO host or deploy it.

## Run locally with your existing Cognite OID access

From the CEPIO repository root, use Python 3.11+:

\`\`\`bash
python -m pip install -e '.[dev]'
python -m pip install 'cognite-sdk>=8,<9'
python scripts/cognite_oid_m0.py \
  --project publicdata \
  --auth interactive \
  --focus compressor \
  --limit 100 \
  --output "$HOME/cepio-oid-m0-inventory.json"
\`\`\`

The interactive flow uses the public Cognite OID Azure AD application registration. It opens sign-in on the user's own computer. **Never paste tokens, secrets or credential files into ChatGPT, GitHub, or PR comments.** If your own shell already has a short-lived authorized bearer token, use \`--auth env\` after supplying \`COGNITE_OID_ACCESS_TOKEN\` securely through the local environment; the script will never echo or persist it.

The output is an owner-only (\`0600\`) JSON document on the local computer. Review it before sharing any excerpt, even though OID is publicly accessible. Do not commit it to CEPIO repositories. The command prints only the output path, project, binding qualification outcome and manifest SHA-256.

If the environment cannot use an interactive browser, run the script on a workstation where you can authenticate; it does not depend on CEPIO's Azure infrastructure.

## Qualification evidence and exit criteria

| Gate | Acceptance | Status before authenticated run |
| --- | --- | --- |
| M0-A project and permission | Authorized \`publicdata\` list/search/retrieve succeeds; no 401/403 | Not verified |
| M0-B evidence inventory | Bounded assets, time series, events, file metadata sampled with explicit sample sizes, missing-unit / association checks and local SHA-256 | Offline code only |
| M0-C source binding | One \`assets/<id>\` resolves through \`qualify_evidence_binding\` with CDF numeric ID and actual \`lastUpdatedTime\` | Offline fake only |
| M0-D compressor scope | Named compressor candidate and linked measurements/events/files verified in the **live** tenant; otherwise report remains not scoped | Not verified |
| M0-E host registration | No CEPIO host registration in M0; status remains \`not-configured\` in production | Deliberately not attempted |
| M0-F downstream value | No industrial decision claim until later blind historical replay | Out of scope |

**Stop conditions:** permission failure, missing version, inconsistent identity, zero candidate compressor scope, inconsistent units, absent timestamps or insufficient historic data must be reported as gaps, not silently fixed or treated as engineering success. Unit changes, timestamp sampling, meter/pressure conversions, process limits and root-cause assertions are for M1+.

## Follow-on milestones

1. **M0 closure:** review local inventory JSON and list candidate compressor asset IDs and associated tags, validate permission and sample coverage.
2. **M1:** agree exact asset/time window, read a bounded historical window, capture provenance and data hashes, verify units/timezone/event gaps, then reconstruct operating state.
3. **M2:** compare LLM only, CEPIO deterministic only and LLM+CEPIO using identical frozen evidence with blinded engineering assessment.
4. **M3:** history-matched decision review and calibrated what-if scenarios in Studio, distinguishing observational correlation from established causal effects.

Provider portability beyond M0 requires comparing **the same underlying frozen evidence** via independent Cognite/Fabric bindings and the **same** Industry IQ Skill/Decision schema. Merely connecting Cognite does not prove G7 portability.

## References

- Cognite OID project and OAuth application information: https://hub.cognite.com/open-industrial-data-211/openid-connect-on-open-industrial-data-993
- Cognite Python SDK v8: https://cognite-sdk-python.readthedocs-hosted.com/en/stable/cognite_client.html
- CEPIO \`docs/developer/platform-bindings.md\`
- CEPIO \`docs/reliability-agent-lighthouse.md\` (G7 portability)

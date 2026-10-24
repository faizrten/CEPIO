# Drilling synthetic testbed migration to CEPIO Labs

The drilling MVP generators, dataset contracts, ground truth and acceptance harness
are maintained in **CEPIO Labs**, not public CEPIO. Scenario Lab remains a protected
Labs capability; this migration is not product-service promotion.

## What moved

The two drilling generators, nine v0.1/v0.2 dataset files, three acceptance/report
scripts and four test modules were imported byte-for-byte before public removal.
Labs reuses those existing assets rather than generating a replacement corpus.
The nine acceptance tests now run in Labs against a pinned public CEPIO runtime.

Destination for authorized maintainers:
[Labs drilling acceptance runbook](https://github.com/faizrten/CEPIO-Labs/tree/main/generalization/scenario-lab/drilling-acceptance).
The replacement landed in
[Labs PR #28](https://github.com/faizrten/CEPIO-Labs/pull/28), commit
`02926c193f0f4e60fe08c90b416898ce346fa8cd`, after its acceptance and catalog CI passed.
Private links require repository access; public contributors do not need that access.

## Contributor workflow

- `make test` continues to run the public runtime/API tests.
- `make validate` runs public SHACL validation, without downloading private datasets
  or invoking a private evaluation suite.
- `make blind-ask` now fails with this migration notice instead of running the old
  public drilling benchmark. It must not be interpreted as an evaluation pass.
- Authorized Labs maintainers use `tools/run_drilling_labs_acceptance.py --core
  /path/to/CEPIO` from Labs, following its pinned-runtime instructions. A new public
  candidate requires a reviewed runtime-pin update and a green Labs acceptance run.
- Public fork CI has no dependency on private repository credentials or datasets.

## Scope and limitations

This is a bounded cutover, not completion of the all-synthetic-in-Labs program.
The synthetic NPT binding adapter remains temporarily in public CEPIO because
Fabric proof code and binding tests depend on it. Its embedded fixture records
must be separated from reusable binding behavior in a subsequent change.
Other embedded synthetic assets still require inventory and migration disposition.

Already-published data remain previously disclosed and recoverable from Git history;
deletion does not make them suitable for hidden qualification. The last pre-cutover
public baseline is `728111d09f8250e56193382c07cc5c7fa798d92b`.
No history is rewritten, customer data introduced, runtime API changed, or release
gate/scorecard advanced by this migration.

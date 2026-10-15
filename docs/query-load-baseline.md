# CEPIO v0.4 Query Load Baseline

The v0.4 Developer Preview includes a repeatable SQLite typed-query reference baseline. Its purpose is to prove that normal SQLite queries use repository-level pushdown rather than materializing the full object population through `runtime.list_objects()`.

## CI reference result

Reference run: CEPIO CI #362 on 2026-10-15.

Environment:

- GitHub-hosted Ubuntu 24.04 runner on Azure;
- Python 3.11.17;
- SQLite reference repository;
- 5,000 current `Compressor` objects;
- equality predicate on `criticality`;
- descending property sort;
- page limit 100;
- `include_total=false`.

Measured result:

```json
{
  "elapsed_ms": 6.306,
  "matched_page": 100,
  "max_ms": 5000.0,
  "objects": 5000,
  "passed": true
}
```

The baseline explicitly replaces `runtime.list_objects()` with a function that raises an assertion. Passing therefore demonstrates that this reference query path did not fall back to full runtime object materialization.

## Reproduce

```bash
PYTHONPATH=src python scripts/query_load_baseline.py --objects 5000 --max-ms 5000
```

The script exits non-zero if the measured query exceeds the supplied threshold or returns an unexpected page size.

## Interpretation

This is a **release regression baseline**, not a production latency SLO and not a universal database benchmark.

The result is sensitive to runner hardware, SQLite version, object shape, predicate selectivity and filesystem/runtime conditions. The 5-second threshold is intentionally generous: it protects against regressions back to pathological execution rather than promising single-digit-millisecond production latency.

Production distributed persistence, horizontal scale, workload-specific performance qualification and SLOs remain part of later enterprise-runtime work.

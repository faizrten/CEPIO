# ADR-0059: Verify quality controls against non-empty changes

Status: Proposed

## Outcome and starting evidence

At main `11148fecd50a8e6bfbf8bdc83c7325137531a14e`, the static and
persisted/public compatibility jobs use `origin/main` outside pull requests.
On a push to main this resolves to the checked-out head, so touched-file
formatting examines no committed changes and compatibility compares head to
itself. PR checks still use the immutable PR base and remain effective.

## Decision and bounded scope

Use the immutable PR base first, then the push's `before` SHA, then `HEAD^`
for calls without either context. Missing or unresolvable bases must fail;
do not silently substitute the current head. Preserve existing thresholds,
required checks, permissions and production boundaries.

Report the formatting input count, and reject a failed untracked-file query.
Exercise the actual aggregate workflow shell command with success, failure,
cancelled, skipped and missing dependency results. Use a temporary Git repo
to prove committed Python changes remain visible after main advances.

The separate CEPIO CI aggregator uses `all(results.values())`, which accepts
empty or incomplete success mappings. GitHub normally supplies every declared
dependency; this is a defensive gap, not evidence of a past bypass. Require the
exact six declared lane names before evaluating results and print their count.

## Acceptance

- A committed Python edit is found using the pre-push revision and is absent
  when compared with the new main, demonstrating the original blind spot.
- Workflow base expressions preserve PR precedence and include push history.
- Required aggregate lanes cannot be skipped, failed, cancelled or absent.
- Non-PR base-coverage skips remain intentional and supported.
- Failed Git enumeration cannot return an apparently empty successful scan.
- Existing authorization, source-integrity and output-contract negative tests
  run unchanged; any execution limitations are recorded separately.

## Non-goals

No runtime, API, ontology, security permission, release status, maturity score,
deployment, paid inference or required-review change. No protected benchmark
or customer data is introduced. This qualifies bounded checks, not the product.

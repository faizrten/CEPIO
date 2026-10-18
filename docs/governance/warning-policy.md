# Warning policy

CEPIO treats unexpected Python warnings as test failures. Warnings are engineering signals, not background log noise, and must not accumulate silently as the codebase grows.

## Default policy

`pytest` runs with `filterwarnings = ["error", ...]`. Any new deprecation, runtime, resource, user or dependency warning therefore fails qualification unless it has an explicit reviewed exception.

Exceptions must be:

- exact in warning message;
- narrow in warning category;
- narrow in originating module where practical;
- documented with ownership and removal intent;
- covered by normal tests so the exception cannot accidentally broaden.

Global filters such as `ignore::DeprecationWarning` are not permitted.

## Current third-party quarantine

CEPIO temporarily ignores exactly:

`Dataset.default_context is deprecated, use Dataset.default_graph instead.`

from `DeprecationWarning` in `rdflib.graph`.

The warning is emitted by the current RDFLib/pySHACL validation path while CEPIO passes ordinary RDFLib `Graph` inputs through `cepio.validation.validate_shacl`. CEPIO does not directly call the deprecated `Dataset.default_context` API. At the time this policy was introduced, hosted qualification resolved RDFLib 7.6.0 and pySHACL 0.40.1 and the repeated upstream warning dominated the warning output.

The exception exists only to preserve a high-signal fail-on-warning policy while that upstream path still emits the deprecation. It should be removed as soon as the resolved dependency path no longer emits the warning. Dependency-update PRs must therefore run the full suite and may delete the quarantine when it is no longer required.

## Regression contract

`tests/test_warning_policy.py` verifies both sides of the policy:

- the committed allowlist contains only the exact RDFLib quarantine after the fail-closed `error` rule;
- an unrelated unexpected `RuntimeWarning` makes an inner pytest qualification run fail.

SHACL correctness is still validated by the existing ontology tests; the warning exception does not alter validation semantics.

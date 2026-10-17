# ADR-0008: Automated quality evidence with solo-maintainer governance

Status: accepted for implementation; activation requires observed check names.

## Decision

Preserve Main Governance v1 and every existing CI command. Add architecture tests,
Ruff lint/format, mypy debt tracking, base-relative compatibility and coverage,
Bandit, dependency audit, CodeQL, and non-publishing release qualification.
Keep approvals at zero, resolved conversations, current-base enforcement, no
bypass actors, and no merge queue. CODEOWNERS records accountability rather than
pretending the author can independently review their own change.

## Scope and tradeoffs

Core boundaries follow the repository's actual flat Python layout. Tests check
imports, profile definitions and governed write dispatch; existing behavioral
security tests cover authorization, replay and external-write ordering. Static
analysis is not a proof against dynamic monkey-patching or arbitrary network I/O.
Canonical ontology changes require an ADR with reusable semantic evidence; a
customer/source term alone is insufficient promotion evidence.

Record the existing lint/type findings by source, diagnostic, and multiplicity.
Reject new findings and require formatting of every touched Python file. Baseline
updates are protected governance changes; they are not an ordinary CI repair.
Coverage compares head with the actual PR base in the same runner environment.
Release evidence qualifies Developer Preview only; production qualification and
publishing remain separate decisions.

## Security exceptions

The three Bandit B608 findings in `external_actions.py` and `query_backend.py`
interpolate fixed SQL fragments, integer-generated aliases, and allowlisted
operators. User values, property paths, identities, and filters are bound as SQL
parameters. Their precise findings are the only Bandit baseline exceptions.
No dependency vulnerability is ignored. Archive extraction now rejects links,
special files, traversal, and destinations outside the temporary repository.
CI's preinstalled setuptools 79.0.1 was vulnerable (CVE-2026-59890); quality
environments, isolated builds and the runtime container now use patched setuptools
83 or newer. The quality environment also pins patched pip 26.2.1.

## Validation

Run negative controls for architecture/import violations, schema removals,
signature changes and DDL changes, plus the full existing suite. CI publishes
compatibility, domain, coverage and security evidence. Require the aggregate
quality gate and CodeQL only after observing their actual check-run names.
The trusted-base `pull_request_target` metadata check never executes PR code.

## Activation evidence

PR #142 merged after every check passed on head `a45bf9d3907a08cd106297ff84bbf8d302dea710`.
The original CI and CodeQL checks passed; base-relative coverage increased from
83.926051% to 84.152698%. The follow-up activation PR exercises the trusted-base
guard now installed on main, adds negative controls for metadata bypasses, and
tests release-manifest hashing and version rejection without publishing artifacts.

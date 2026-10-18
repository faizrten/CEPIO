# Local preflight

Use local preflight to catch most merge failures before opening or updating a pull request. Hosted GitHub qualification remains authoritative.

## Install

```bash
python -m pip install -e '.[dev]' -r requirements-quality.txt
```

Fetch the PR base before running preflight:

```bash
git fetch origin main
```

## Fast iteration

```bash
make preflight-fast
```

`preflight-fast` runs the touched-file quality/type ratchet, security scan, API/client/ontology contracts and deterministic targeted tests. Test selection is reported with the reason each test was chosen. Architecture and quality-governance tests are always included.

To compare against another base:

```bash
BASE_REF=origin/feature-branch make preflight-fast
```

Fast mode is intentionally **not** a merge qualification replacement. It exists to reduce feedback latency during implementation.

## Full local qualification

```bash
make preflight-full
```

Full mode runs the same underlying repository scripts used by hosted CI where practical: quality/security checks, full pytest, query/deployment/API/client/ontology validation, drilling and refinery qualification, deterministic validation, reference demo, wheel build and installed-wheel smoke.

The local wheel smoke installs the freshly built wheel into a temporary virtual environment outside the repository checkout, removes `PYTHONPATH`, verifies imports come from the installed artifact, resolves packaged ontology/profile resources and boots the SATORP reference runtime. It uses the already installed development dependencies for speed; hosted CI remains responsible for the stricter isolated dependency-install smoke.

Hosted CI additionally remains authoritative for protected workflow behavior, immutable PR-base coverage comparison, CodeQL, fully isolated package installation, container smoke and branch-governance enforcement.

## Evidence

Both modes write `evidence/local-preflight.json`, including:

- resolved base reference;
- changed files;
- selected fast tests and selection reasons;
- every command executed;
- command duration and return code;
- aggregate duration and pass/fail state.

The `evidence/` directory is gitignored. Preflight fails on the first failed step and retains the report produced up to that point.

# CEPIO Runtime Configuration and Packaging

CEPIO runtime configuration is environment-driven. Source-tree-relative paths are a development fallback, not the production contract.

## Runtime settings

| Setting | Purpose | Default |
|---|---|---|
| `CEPIO_ENVIRONMENT` | `development`, `test`, or production environment name | `development` |
| `CEPIO_DB_URL` | persistence configuration | `memory://` only in development/test; required otherwise |
| `CEPIO_RESOURCE_ROOT` | override root containing canonical CEPIO resources | packaged resources / source fallback |
| `CEPIO_ONTOLOGY_DIR` | override ontology directory | `<resource-root>/ontologies` |
| `CEPIO_PROFILES` | comma-separated customer profiles | empty until profiles are selected |
| `CEPIO_VALIDATE_TYPES` | ontology type validation | `true` |
| `CEPIO_VALIDATE_PROPERTIES` | canonical property validation | `true` |
| `CEPIO_STRICT_PROPERTIES` | reject undeclared datatype properties | `false` |

### Reference persistence URLs

```text
memory://
sqlite:///cepio.db
sqlite:////absolute/path/cepio.db
```

The reference runtime intentionally fails fast on unsupported persistence URLs. Production repository adapters can extend this contract without changing application semantics.

In a non-development environment, omitting `CEPIO_DB_URL` is a startup error. This prevents an accidental in-memory production deployment.

## Packaged resources

Wheel builds bundle the canonical runtime assets under `cepio.resources`:

```text
ontology-modules.yaml
ontologies/
mappings/
shapes/
actions/
policies/
```

Runtime resolution order is:

1. explicit resource-root argument;
2. `CEPIO_RESOURCE_ROOT`;
3. installed `cepio.resources` through `importlib.resources`;
4. repository root for editable/source development.

This allows an installed wheel to bootstrap from any working directory without relying on the Git checkout.

## Version source

`src/cepio/_version.py` is the single package version source. `pyproject.toml`, `cepio.__version__`, FastAPI metadata, and `/health` consume that value.

The CEPIO Python distribution version is `0.4.1`, including the explicit Azure AI Search provider retirement (ADR-0039). This packaging change does not qualify the separate CEPIO v0.5 CONNECT product release.

## Health metadata

`GET /health` reports:

- package version;
- ontology catalogue schema version;
- all loaded canonical module versions;
- loaded customer-profile versions (populated by the profile loader workstream).

## CI packaging gate

CI builds a wheel, creates a clean virtual environment, installs the wheel, changes to `/tmp` outside the repository, resolves packaged resources, and boots a CEPIO runtime. A packaging change is not complete if this smoke test fails.

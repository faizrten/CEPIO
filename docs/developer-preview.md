# CEPIO v0.4 Developer Preview

CEPIO v0.4 is the first release intended to be consumed as a **Developer Preview** rather than only as a repository-level reference implementation.

The supported entry point is the versioned REST contract under `/api/v1`. The release remains intentionally narrower than a production platform: SQLite is a single-writer reference backend, live industrial writeback is deferred to v0.5, and enterprise HA/SLO/DR qualification is deferred to later releases.

## What this guide proves

A clean environment can:

1. build and install the CEPIO wheel outside the repository checkout;
2. start the packaged API and call `/api/v1/health`;
3. build and start the reference container;
4. authenticate with development identity locally or Microsoft Entra ID in production configuration;
5. use the public API v1 contract through the validated Python or TypeScript reference clients;
6. deploy the same runtime image through the App Service or AKS reference profiles.

## Prerequisites

- Python 3.11+
- Git
- Docker for the container path
- Azure CLI only when deploying the App Service profile
- `kubectl` only when deploying the AKS profile

## Clean wheel path

From a clean checkout:

```bash
python -m venv .venv-build
. .venv-build/bin/activate
python -m pip install --upgrade pip build
python -m build --wheel
```

Install the resulting wheel into a separate environment and leave the repository directory:

```bash
python -m venv /tmp/cepio-v04
/tmp/cepio-v04/bin/python -m pip install dist/cepio-*.whl
cd /tmp
```

Start CEPIO in local development-auth mode:

```bash
CEPIO_ENVIRONMENT=test \
CEPIO_DB_URL=memory:// \
CEPIO_AUTH_MODE=dev \
/tmp/cepio-v04/bin/uvicorn cepio.public_api:app --host 127.0.0.1 --port 8000
```

In another shell:

```bash
curl --fail http://127.0.0.1:8000/api/v1/health
```

This is the same packaging boundary exercised by CI. Package resources such as ontology modules, mappings, policies and customer profiles must resolve from the installed wheel rather than the source checkout.

## Clean container path

Build the portable runtime image:

```bash
docker build -t cepio:v0.4-dev-preview .
```

Run it locally:

```bash
docker run --rm -p 8000:8000 \
  -e CEPIO_ENVIRONMENT=test \
  -e CEPIO_DB_URL=memory:// \
  -e CEPIO_AUTH_MODE=dev \
  cepio:v0.4-dev-preview
```

Then verify:

```bash
curl --fail http://127.0.0.1:8000/api/v1/health
```

The release CI performs an equivalent container startup/health smoke test so a successful release-gate run proves that the image starts independently of an editable Python checkout.

## Authentication

For local/test use, explicit development identity headers are available only with a non-production environment and `CEPIO_AUTH_MODE=dev`:

```bash
curl \
  -H 'X-CEPIO-Dev-Actor: developer' \
  -H 'X-CEPIO-Dev-Roles: cepio_admin' \
  http://127.0.0.1:8000/api/v1/objects
```

For production configuration, use Microsoft Entra ID:

```text
CEPIO_ENVIRONMENT=production
CEPIO_AUTH_MODE=entra
CEPIO_ENTRA_TENANT_ID=<tenant-id>
CEPIO_ENTRA_AUDIENCE=<API application ID URI or client ID>
CEPIO_DB_URL=<explicit persistence URL>
```

Callers send an Entra access token as `Authorization: Bearer <token>`. Actor identity and roles are derived from validated claims and cannot be elevated through request payloads. See [REST Security Boundary](rest-security.md).

## Public API and clients

The accepted public route baseline is `openapi/cepio-v1.yaml`. CI checks the runtime route/method/operation-ID set against that baseline and separately checks the Python and TypeScript client operation maps against the same baseline.

This validation is deliberately described as **route-contract validation**. v0.4 does not yet claim full generated-client/schema compatibility for every request and response field.

- Python: `cepio.sdk.CEPIOClient`
- TypeScript reference source: `clients/typescript/cepio.ts`
- Client usage: [API Client Guide](api-client-guide.md)
- Error/concurrency/idempotency semantics: [API Reliability Semantics](api-reliability.md)
- Request examples: [API Examples](api-examples.md)

## Query scale reference

The SQLite reference backend runs the typed-query load baseline in CI without falling back to `runtime.list_objects()`. See [Query Load Baseline](query-load-baseline.md) for the measured reference result and its limitations.

## Microsoft hosting profiles

The same container contract is used by:

- App Service: `deploy/appservice/main.bicep`
- AKS: `deploy/aks/cepio.yaml`

See [Reference Deployment Profiles](deployment-profiles.md). These are reproducible reference profiles, not a claim that CEPIO v0.4 provides a horizontally scalable production persistence plane.

## Observability

Runtime repository, policy, function and action activity can emit sanitized telemetry through the backend-neutral CEPIO telemetry sink. An optional OpenTelemetry adapter is available through the `otel` package extra. See [Observability](observability.md).

## Release qualification commands

The release gate is represented in CI by the following families of checks:

```bash
pytest -q
PYTHONPATH=src python scripts/query_load_baseline.py --objects 5000 --max-ms 5000
PYTHONPATH=src python scripts/validate_deployment_profiles.py
PYTHONPATH=src python scripts/check_api_contract.py
PYTHONPATH=src python scripts/check_client_contract.py
PYTHONPATH=src python scripts/check_ontology_compat.py --json-report compatibility-report.json
make validate
PYTHONPATH=src python examples/demo.py
python -m build --wheel
```

CI additionally installs the wheel outside the repository and starts the built container before the Developer Preview gate is considered satisfied.

## Release boundary

Read [RELEASE.md](../RELEASE.md) before relying on a capability. It distinguishes the v0.4 Developer Preview supported surface from experimental, reference-only and deferred functionality.

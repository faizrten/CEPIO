# Deployment and Operations

## Current state

CEPIO can be run locally and tested cloud-independently. The current roadmap focus is formal Microsoft-native deployment profiles.

## Local/reference deployment

Requirements include Python 3.11+.

```bash
git clone https://github.com/faizrten/CEPIO.git
cd CEPIO
python -m pip install -e '.[dev]'
pytest -q
make validate
PYTHONPATH=src python examples/demo.py
```

Start the API:

```bash
uvicorn cepio.api:app --reload
```

API documentation is available from the FastAPI OpenAPI UI during local execution.

## Persistence

Reference persistence can use SQLite:

```python
from cepio.bootstrap import build_runtime
runtime = build_runtime(sqlite_path="cepio.db")
```

SQLite is a reference implementation, not the target enterprise-scale runtime.

## App Service profile — roadmap/current priority

Intended scope:

- REST and MCP endpoints;
- managed identity;
- private networking;
- health and readiness endpoints;
- deployment slots;
- autoscale;
- application configuration;
- secretless patterns.

## AKS profile — roadmap/current priority

Intended scope:

- horizontally scalable runtime;
- event workers/projectors;
- source-system adapters;
- Entra Workload Identity;
- private networking;
- Key Vault integration;
- probes;
- autoscaling;
- workload isolation;
- controlled rollout.

## NVIDIA profile

GPU acceleration is optional and must not become a baseline dependency.

The architectural rule is:

> CPU/reference semantics remain authoritative; GPU acceleration is an execution optimization.

## Observability — next priority

OpenTelemetry coverage should include:

- query execution;
- repository access;
- function calls;
- policy decisions;
- MCP tool calls;
- actions;
- adapters;
- projectors.

Desired telemetry:

- latency;
- success/failure;
- trace correlation;
- retry/reconciliation signals.

Industrial data must not be leaked into telemetry by default.

## SRE direction for later releases

Production platformization will require:

- SLOs/SLIs;
- HA architecture;
- backup/restore;
- disaster recovery;
- capacity planning;
- multi-tenancy isolation;
- secrets lifecycle;
- vulnerability management;
- upgrade/rollback automation;
- performance benchmarking.

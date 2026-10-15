# CEPIO runtime observability

CEPIO exposes a backend-neutral telemetry contract for runtime operations. The core package does not require OpenTelemetry unless the optional `otel` extra is installed.

## What is emitted

The runtime can emit structured events for:

- repository calls;
- policy evaluation;
- function execution;
- action execution and policy rejection;
- adapter/integration calls through the public `telemetry_operation(...)` boundary.

Every event contains:

- category and operation;
- success/failure;
- duration in milliseconds;
- timestamp;
- a small allowlisted set of identifiers/status attributes.

CEPIO telemetry must not contain object properties, action parameters, handler effects, policy reasons, source records, credentials, or other protected payloads.

## In-memory capture

```python
from cepio.bootstrap import build_runtime
from cepio.observability import InMemoryTelemetrySink

sink = InMemoryTelemetrySink()
runtime = build_runtime(telemetry_sink=sink)

# use runtime normally
for event in sink.events:
    print(event.category, event.operation, event.duration_ms, event.success)
```

This sink is intended for unit tests and local diagnostics.

## OpenTelemetry

Install the optional integration:

```bash
pip install 'cepio[otel]'
```

Then attach the adapter:

```python
from cepio.bootstrap import build_runtime
from cepio.observability import OpenTelemetrySink

runtime = build_runtime(telemetry_sink=OpenTelemetrySink())
```

The adapter uses the active OpenTelemetry tracer provider. Export, sampling, Application Insights/Azure Monitor wiring, and collector configuration remain deployment concerns rather than CEPIO semantic/runtime dependencies.

## Adapter instrumentation

Future SAP, PI, OSDU, P6 and other connectors should use the same telemetry contract:

```python
from cepio.observability import telemetry_operation

with telemetry_operation(
    runtime.telemetry_sink,
    category="adapter",
    operation="read",
    attributes={"adapter": "sap-s4", "resource": "equipment"},
):
    records = source.read_equipment()
```

Only identifiers and operational metadata should be attached. Do not attach `records` or source payload fields.

## Event naming

Current categories are:

- `repository`
- `policy`
- `function`
- `action`
- `adapter`

Backends may project these events into traces, metrics, logs, Application Insights, Azure Monitor, Grafana, or another observability platform without changing CEPIO-Core semantics.

# CEPIO API v1 Client Guide

CEPIO v0.4 Developer Preview exposes the supported public HTTP surface under `/api/v1`.

Both reference clients are checked in CI against the route/method/operation-ID baseline in `openapi/cepio-v1.yaml`. This is route-contract validation; v0.4 does not claim that every schema is generated from OpenAPI.

## Python client

The Python client is shipped in the CEPIO wheel:

```python
from cepio.sdk import CEPIOClient

client = CEPIOClient(
    "https://<cepio-host>",
    access_token="<entra-access-token>",
)
health = client.health()
asset, etag = client.get_object_with_etag("K-201")
client.close()
```

For local/test development identity:

```python
client = CEPIOClient(
    "http://127.0.0.1:8000",
    dev_actor="developer",
    dev_roles={"cepio_admin"},
)
```

The client rejects simultaneous Entra-token and development-header configuration.

### Optimistic concurrency

```python
asset, _ = client.get_object_with_etag("K-201")
asset.name = "Recycle Gas Compressor K-201"
stored = client.upsert_object(asset, expected_version=asset.version)
```

`expected_version` is sent through the public `If-Match` header rather than the legacy query parameter.

### Cursor query

```python
from cepio.query import ObjectQuery, PropertyPredicate, QueryOperator

page = client.query_objects(
    ObjectQuery(
        object_type="Compressor",
        predicates=[
            PropertyPredicate(
                property="criticality",
                operator=QueryOperator.eq,
                value="high",
            )
        ],
        limit=100,
        include_total=False,
    )
)

if page.next_cursor:
    next_page = client.query_objects(
        ObjectQuery(
            object_type="Compressor",
            limit=100,
            include_total=False,
            cursor=page.next_cursor,
        )
    )
```

A cursor is opaque and bound to its query shape. Do not modify or combine it with offset pagination.

### Governed action

```python
from cepio.model import ActionRequest, ObjectRef

result = client.execute_action(
    ActionRequest(
        action_type="CreateWorkOrder",
        target=ObjectRef(id="K-201", type="Compressor"),
        actor_id="ignored-by-http-client",
        actor_roles=set(),
        parameters={"priority": "high"},
    ),
    idempotency_key="k201-work-order-001",
)
```

The Python HTTP client intentionally does not send `actor_id` or `actor_roles` as authority. Identity is established by the authenticated HTTP context.

## TypeScript reference client

`clients/typescript/cepio.ts` is a source-level reference client for browser/server TypeScript consumers. In v0.4 it is not published as an npm package and is not yet a generated SDK.

```ts
import { CEPIOClient } from "./cepio";

const client = new CEPIOClient("https://<cepio-host>", {
  accessToken: "<entra-access-token>",
});

const health = await client.health();
const { object, etag } = await client.getObject("K-201");
```

Local/test development identity:

```ts
const client = new CEPIOClient("http://127.0.0.1:8000", {
  devActor: "developer",
  devRoles: ["cepio_admin"],
});
```

Optimistic update:

```ts
const { object } = await client.getObject("K-201");
object.name = "Recycle Gas Compressor K-201";
const stored = await client.upsertObject(object, object.version);
```

Idempotent action:

```ts
const result = await client.executeAction(
  {
    action_type: "CreateWorkOrder",
    target: { id: "K-201", type: "Compressor" },
    parameters: { priority: "high" },
  },
  "k201-work-order-001",
);
```

## Contract validation

Run:

```bash
PYTHONPATH=src python scripts/check_client_contract.py
```

The check fails if either client is missing, adds, or changes an operation ID, HTTP method or route relative to `openapi/cepio-v1.yaml`.

For request/response semantics, use the public API tests and the specific guides for queries, authentication and reliability semantics; the committed OpenAPI v0.4 baseline is not yet a complete schema-code-generation contract.

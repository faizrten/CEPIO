# CEPIO Public API v1 Examples

These examples use the supported `/api/v1` surface qualified for the CEPIO v0.4 Developer Preview.

Set a base URL and Entra token for a production-configured endpoint:

```bash
export CEPIO_URL='https://<cepio-host>'
export CEPIO_TOKEN='<entra-access-token>'
```

For local development mode, replace the bearer header in the examples with:

```text
-H 'X-CEPIO-Dev-Actor: developer' \
-H 'X-CEPIO-Dev-Roles: cepio_admin,maintenance_engineer,auditor'
```

## Health

```bash
curl --fail "$CEPIO_URL/api/v1/health"
```

## Read an object and capture its ETag

```bash
curl -i \
  -H "Authorization: Bearer $CEPIO_TOKEN" \
  "$CEPIO_URL/api/v1/objects/K-201"
```

The response includes an object-version `ETag`, for example `"3"`.

## Optimistic object update

```bash
curl -X PUT \
  -H "Authorization: Bearer $CEPIO_TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'If-Match: "3"' \
  "$CEPIO_URL/api/v1/objects/K-201" \
  -d '{
    "id": "K-201",
    "type": "Compressor",
    "name": "Recycle Gas Compressor K-201",
    "properties": {"criticality": "high"},
    "interfaces": ["MaintainableAsset"]
  }'
```

A stale object version returns HTTP `409` rather than overwriting the current state.

## Cursor-based typed query

```bash
curl -X POST \
  -H "Authorization: Bearer $CEPIO_TOKEN" \
  -H 'Content-Type: application/json' \
  "$CEPIO_URL/api/v1/query/objects" \
  -d '{
    "object_type": "Compressor",
    "predicates": [
      {"property": "criticality", "operator": "eq", "value": "high"}
    ],
    "sort": [{"field": "name", "direction": "asc"}],
    "limit": 100,
    "include_total": false
  }'
```

When `has_more` is true, send the returned `next_cursor` in an otherwise equivalent query. The cursor is opaque and must not be combined with `offset`.

## Call a typed function

```bash
curl -X POST \
  -H "Authorization: Bearer $CEPIO_TOKEN" \
  -H 'Content-Type: application/json' \
  "$CEPIO_URL/api/v1/functions/calculateAssetRisk" \
  -d '{"arguments": {"asset_id": "K-201"}}'
```

## Execute a governed idempotent action

```bash
curl -X POST \
  -H "Authorization: Bearer $CEPIO_TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: k201-work-order-001' \
  "$CEPIO_URL/api/v1/actions" \
  -d '{
    "action_type": "CreateWorkOrder",
    "target": {"id": "K-201", "type": "Compressor"},
    "parameters": {"priority": "high"},
    "correlation_id": "reliability-case-001"
  }'
```

Do not send caller-controlled `actor_id` or `actor_roles` as authority. CEPIO derives actor context from the authenticated request.

## Persist a decision

```bash
curl -X POST \
  -H "Authorization: Bearer $CEPIO_TOKEN" \
  -H 'Content-Type: application/json' \
  "$CEPIO_URL/api/v1/decisions" \
  -d '{
    "subject": {"id": "K-201", "type": "Compressor"},
    "problem": "Elevated reliability risk",
    "observations": ["Repeated trip history"],
    "recommendation": "Inspect bearings before next operating window",
    "recommended_action": "CreateInspection",
    "confidence": 0.82
  }'
```

`created_by` is derived by the server from the authenticated caller rather than trusted from the payload.

## Record an operational event

```bash
curl -X POST \
  -H "Authorization: Bearer $CEPIO_TOKEN" \
  -H 'Content-Type: application/json' \
  "$CEPIO_URL/api/v1/events" \
  -d '{
    "type": "TripEvent",
    "subject": {"id": "K-201", "type": "Compressor"},
    "severity": "high",
    "properties": {}
  }'
```

## Audit

An actor with `auditor` or `cepio_admin` can query the action audit surface:

```bash
curl \
  -H "Authorization: Bearer $CEPIO_TOKEN" \
  "$CEPIO_URL/api/v1/audit?target_id=K-201"
```

## Request correlation

Supply an external request ID when integrating CEPIO into a distributed workflow:

```bash
curl \
  -H "Authorization: Bearer $CEPIO_TOKEN" \
  -H 'X-Request-ID: plant-a-case-12345' \
  "$CEPIO_URL/api/v1/objects/K-201"
```

CEPIO returns the request ID in `X-Request-ID`, and public API error envelopes expose it as `requestId`.

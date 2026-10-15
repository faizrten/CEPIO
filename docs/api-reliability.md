# CEPIO API v1 Reliability Semantics

This document describes the public error, request-correlation, optimistic-concurrency and idempotency behavior qualified for the CEPIO v0.4 Developer Preview.

## Request correlation

Every `/api/v1` response carries `X-Request-ID`.

- If the caller supplies `X-Request-ID`, CEPIO propagates it.
- Otherwise CEPIO creates a request ID.
- Public v1 error bodies include the same identifier as `requestId`.

## Public error envelope

Public v1 HTTP and request-validation failures use:

```json
{
  "code": "version_conflict",
  "message": "Object K-201 version mismatch: expected 3, actual 4",
  "requestId": "<request-id>",
  "details": {}
}
```

`code` is intended for programmatic handling. `message` is explanatory text. `details` contains structured contextual information where available.

Important stable v0.4 codes include:

- `authentication_required`
- `forbidden`
- `not_found`
- `version_conflict`
- `request_validation`
- `semantic_validation`
- `query_validation`
- `invalid_query_cursor`
- `query_budget_exceeded`
- `idempotency_key_conflict`
- `invalid_if_match`

## ETag and If-Match

`GET /api/v1/objects/{object_id}` returns the CEPIO object version as an HTTP `ETag`, for example:

```text
ETag: "3"
```

Use that version when replacing the object:

```http
PUT /api/v1/objects/K-201
If-Match: "3"
Content-Type: application/json
```

If the stored object has moved to a different version, CEPIO returns HTTP `409` rather than silently overwriting a newer state.

Weak ETag syntax such as `W/"3"` is accepted. Non-numeric object-version tags fail with HTTP `400` and `invalid_if_match`.

The Python and TypeScript v1 clients expose this through `expected_version` / `expectedVersion`.

## Idempotency-Key

Governed actions accept an HTTP `Idempotency-Key`:

```http
POST /api/v1/actions
Idempotency-Key: k201-work-order-001
```

CEPIO scopes action idempotency by actor, action type and target before caching/replaying a prior action result. A successful replay is marked as replayed in the action result and is audited.

For compatibility, the request body can still contain the deprecated `idempotency_key` field. If both header and body values are present and differ, CEPIO fails with HTTP `400` and `idempotency_key_conflict`.

New clients should use the HTTP header.

## Identity and idempotency

Idempotency does not weaken authorization. Policy evaluation occurs within the governed action path and authenticated actor identity comes from the HTTP security context. The client cannot create a broader replay scope by supplying another actor identity in the action payload.

## Query protection

Typed queries have explicit complexity/execution budgets. A request exceeding a configured budget returns HTTP `429` with `query_budget_exceeded`.

Opaque cursors are bound to the query they continue. Invalid or query-mismatched cursors return HTTP `400` with `invalid_query_cursor`.

Authorization/property filtering is applied before exposed totals, cursor positions and page results.

## Developer Preview boundary

The v0.4 error envelope normalizes public HTTP and request-validation failures handled by the versioned API layer. It is not yet a claim that every unexpected internal Python exception is converted into a fully typed domain-specific error code. Production-wide fault taxonomy and SLOs remain later enterprise-runtime work.

# REST Security Boundary

CEPIO REST is authenticated by default. `/health` is the only anonymous route.

## Authentication modes

### Production: Microsoft Entra ID

Set:

```text
CEPIO_ENVIRONMENT=production
CEPIO_AUTH_MODE=entra
CEPIO_ENTRA_TENANT_ID=<tenant-id>
CEPIO_ENTRA_AUDIENCE=<API application ID URI or client ID>
```

Optional overrides:

```text
CEPIO_ENTRA_ISSUER=<issuer>
CEPIO_ENTRA_JWKS_URI=<jwks endpoint>
CEPIO_GROUP_ROLE_MAP={"<group-object-id>":["maintenance_engineer"]}
```

The REST layer validates token signature, issuer, audience and lifetime. CEPIO actor identity is derived from `oid` (falling back to `sub`). CEPIO roles are derived from the Entra `roles` claim plus any explicitly configured group-to-role mappings.

Clients cannot grant themselves roles through request bodies. Deprecated `actor_id` / `actor_roles` action fields are ignored as authority inputs; inconsistent claims are rejected and audited.

## Development identity mode

A header-based development identity is available only when both settings are explicit:

```text
CEPIO_ENVIRONMENT=development   # or test
CEPIO_AUTH_MODE=dev
```

Then requests may provide:

```text
X-CEPIO-Dev-Actor: developer
X-CEPIO-Dev-Roles: cepio_admin,maintenance_engineer
```

`CEPIO_AUTH_MODE=dev` with `CEPIO_ENVIRONMENT=production` fails closed and cannot be used as a production bypass.

## Read authorization

Authenticated reads are evaluated against CEPIO policy before data is returned.

Policy can restrict:

- object types through `read_types`;
- object sharing scope through `read_scopes` and the object's `sharingScope` / `sharing_scope` property;
- properties through `read_properties`.

Actor-scoped typed queries apply object and property visibility **before predicates, totals, sorting and pagination**. This prevents hidden objects or hidden properties from being inferred through query counts.

Neighbour traversal also filters returned objects using the same policy boundary. Audit access requires `auditor` or `cepio_admin`. Graph-wide analytical endpoints require `graph_analyst`, `auditor` or `cepio_admin` until graph analytics supports fully actor-scoped subgraphs.

## Direct mutation endpoints

Low-level object and relationship mutation is restricted to `cepio_admin`. Domain changes should normally flow through governed CEPIO actions rather than generic CRUD.

## Security invariants

1. Caller identity and roles originate from authenticated hosting/token context, not model/client arguments.
2. Authorization applies to reads as well as actions.
3. Restricted properties cannot be used as a side channel through actor-scoped typed queries.
4. Sharing-scope policy is evaluated before an object becomes visible.
5. Development authentication cannot be enabled in production configuration.
6. Action identity spoof attempts are rejected and audited.

# Authenticated hosted API access preflight

The manual `CEPIO API Read-only Access Check` workflow uses the existing protected `azure-demo` environment and Azure deployment identity. It runs on main only and pins the existing `cepio-demo-31d48.azurewebsites.net` host. It does not deploy or change Azure resources or role assignments.

After merge, run the workflow from Actions and satisfy any existing environment approval. It reads the configured CEPIO audience, requests an access token for that resource, and performs GET requests to `/api/v1/objects` and `/management/v1/health`. Tokens and response bodies are never printed or uploaded. Redirects are refused. No model calls or Actions occur.

A GUID audience assumes the conventional `api://<GUID>` App ID URI; a configured URI is used exactly. Token acquisition failure can mean a nonstandard App ID URI, missing resource consent, or identity access. The workflow intentionally does not guess alternate identities or grant permissions. Azure metadata/token failures are reported with a fixed code to avoid leaking raw CLI output.

HTTP 401 means authenticated access has not been established. HTTP 403 means the request was denied; inspect the required app role before requesting a narrowly scoped assignment. Management access is reported independently and is not required for an Application API read check. HTTP 200 for object listing can represent a filtered or empty dataset and does not prove access to specific drilling assets.

This is access evidence only, not top-drive/mud-pump scenario qualification, paid Foundry connectivity, approval enforcement, or live industrial integration. The deployment identity is reused only for this diagnostic; any ongoing scenario identity and permissions must be explicitly scoped. Do not grant administrator access to make this check pass.

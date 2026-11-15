"""Host-only OSDU Storage v2 versioned reads; no DDMS bulk-data claim.

The host must authorize each call and supply a source token scoped to the actor.
Never expose this client, its endpoint configuration or credentials to agents.
"""
from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote, urlsplit

import httpx

from cepio.domain_bindings import ExternalRecordReference


class OSDUReadError(RuntimeError):
    """Sanitized source failure; response bodies and credentials are never included."""


class OSDURecordReader:
    def __init__(
        self, endpoint: str, partition: str, token_provider: Callable[[], str],
        *, transport: httpx.BaseTransport | None = None, max_bytes: int = 1_000_000,
    ) -> None:
        url = urlsplit(endpoint)
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or url.query or url.fragment):
            raise ValueError("Host-configured HTTPS endpoint required")
        if not partition or any(c.isspace() for c in partition):
            raise ValueError("Invalid partition")
        if max_bytes <= 0:
            raise ValueError("Positive response limit required")
        self._endpoint = endpoint.rstrip("/")
        self._partition = partition
        self._token_provider = token_provider
        self._transport = transport
        self._max_bytes = max_bytes

    def read(self, reference: ExternalRecordReference) -> dict:
        """Read an exact source version after host policy authorization.

        Returns the source record transiently, including ACL/legal metadata.
        Does not persist, cache, register readiness, or interpret domain payloads.
        """
        version = str(reference.record_version or "")
        if (reference.source_system != "osdu" or reference.partition != self._partition
                or not reference.record_id or not reference.record_kind
                or not version.isascii() or not version.isdecimal() or int(version) <= 0):
            raise OSDUReadError("INVALID_SOURCE_REFERENCE")
        token = self._token_provider()
        if not token or any(c.isspace() for c in token):
            raise OSDUReadError("SOURCE_AUTH_REQUIRED")
        path = f"/api/storage/v2/records/{quote(reference.record_id, safe='')}/{version}"
        try:
            with httpx.Client(transport=self._transport, timeout=20, follow_redirects=False,
                              trust_env=False) as client:
                with client.stream("GET", self._endpoint + path, headers={
                    "Authorization": f"Bearer {token}",
                    "data-partition-id": self._partition,
                    "Accept": "application/json",
                }) as response:
                    if response.status_code != 200:
                        code = {401: "SOURCE_ACCESS_DENIED", 403: "SOURCE_ACCESS_DENIED",
                                404: "SOURCE_RECORD_NOT_FOUND"}.get(
                                    response.status_code, "SOURCE_UNAVAILABLE")
                        raise OSDUReadError(code)
                    payload = bytearray()
                    for chunk in response.iter_bytes():
                        payload.extend(chunk)
                        if len(payload) > self._max_bytes:
                            raise OSDUReadError("SOURCE_RESPONSE_TOO_LARGE")
            import json
            record = json.loads(payload)
        except (httpx.HTTPError, ValueError):
            raise OSDUReadError("SOURCE_RESPONSE_INVALID") from None
        if (not isinstance(record, dict) or record.get("id") != reference.record_id
                or str(record.get("version")) != version
                or record.get("kind") != reference.record_kind):
            raise OSDUReadError("SOURCE_IDENTITY_MISMATCH")
        if (not isinstance(record.get("data"), dict)
                or not isinstance(record.get("acl"), dict)
                or not isinstance(record.get("legal"), dict)):
            raise OSDUReadError("SOURCE_METADATA_MISSING")
        return record

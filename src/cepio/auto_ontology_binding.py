"""Host-only Auto-Ontology catalog binding; no semantic approval or data query.

The host supplies per-call identity, policy and caller-scoped HTTP credentials.
This module is not an authentication boundary or a public tool entry point.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from urllib.parse import urlsplit

import httpx

from .auth import ActorContext
from .domain_bindings import ExternalRecordReference
from .platform_bindings import (
    BindingCapability,
    BindingMode,
    EvidenceEnvelope,
    PlatformBindingManifest,
)

UPSTREAM_REVISION = "fc43a82600e18b19d159c52023f54f5572f537ac"


class AutoOntologyReadError(RuntimeError):
    """Sanitized upstream failure; response bodies and credentials stay private."""


class AutoOntologyTermBinding:
    """Read one allowlisted glossary record as unapproved semantic evidence.

    Construct per authenticated request. Never deserialize constructor arguments
    from an agent request. The authorize callback must check current source-use
    permission on every read; the HTTP client must belong to that same principal.
    No global registration, cache, ontology mutation or model invocation occurs.
    """

    def __init__(
        self,
        *,
        origin: str,
        tenant_id: str,
        actor_id: str,
        term_ids: frozenset[str],
        client: httpx.Client,
        principal: Callable[[], ActorContext],
        authorize: Callable[[ActorContext, str], bool],
    ) -> None:
        parts = urlsplit(origin)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.path not in ("", "/")
            or parts.query
            or parts.fragment
        ):
            raise ValueError("origin must be a trusted HTTPS origin without credentials")
        if not tenant_id.strip() or not actor_id.strip():
            raise ValueError("host tenant and actor are required")
        if not term_ids or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", t) for t in term_ids):
            raise ValueError("explicit safe term identifiers are required")
        self._origin = origin.rstrip("/")
        self._tenant = tenant_id
        self._actor = actor_id
        self._terms = frozenset(term_ids)
        self._client = client
        self._principal = principal
        self._authorize = authorize
        self.manifest = PlatformBindingManifest(
            binding_id="nvidia.auto-ontology.catalog.v0.1",
            provider_id="nvidia-auto-ontology",
            source_system=self._origin,
            mode=BindingMode.evidence,
            capabilities=frozenset({BindingCapability.resolve_evidence}),
        )

    def resolve_evidence(self, external_id: str) -> EvidenceEnvelope:
        actor = self._principal()
        if actor.tenant_id != self._tenant or actor.actor_id != self._actor:
            raise PermissionError("Auto-Ontology host principal mismatch")
        if external_id not in self._terms:
            raise PermissionError("Auto-Ontology term is outside host scope")
        if self._authorize(actor, external_id) is not True:
            raise PermissionError("Auto-Ontology source use denied")
        uri = f"{self._origin}/api/terms/{external_id}"
        try:
            # Never follow a redirect carrying the host client's credentials.
            with self._client.stream("GET", uri, follow_redirects=False, timeout=15) as res:
                if res.status_code != 200:
                    raise AutoOntologyReadError("Auto-Ontology term read failed")
                body = bytearray()
                for chunk in res.iter_bytes():
                    body.extend(chunk)
                    if len(body) > 262144:
                        raise AutoOntologyReadError("Auto-Ontology term exceeds size limit")
            payload = json.loads(body)
        except (httpx.HTTPError, ValueError):
            raise AutoOntologyReadError("Auto-Ontology transport or JSON failure") from None
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
            raise AutoOntologyReadError("Auto-Ontology term response shape mismatch")
        term = payload["data"]
        if term.get("id") != external_id:
            raise AutoOntologyReadError("Auto-Ontology term identity mismatch")
        digest = hashlib.sha256(bytes(body)).hexdigest()
        return EvidenceEnvelope(
            reference=ExternalRecordReference(
                source_system=self._origin,
                record_kind="semantic-term",
                record_id=external_id,
                partition=self._tenant,
                source_uri=uri,
                metadata={"response_sha256": digest, "upstream_revision": UPSTREAM_REVISION},
            ),
            evidence={
                "term": term,
                "cepio_status": "proposal-only",
                "evidence_kind": "semantic-metadata",
            },
        )

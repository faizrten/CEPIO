"""Adversarial tests using real Core policy, registry and Skill preflight."""

import asyncio
from dataclasses import replace
from datetime import timedelta
import json
from pathlib import Path
import runpy

import pytest

from cepio.accc_readonly import CompositionRequest
from cepio.accc_runtime_binding import contract_hash
from cepio.auth import ActorContext


@pytest.fixture
def demo():
    module = runpy.run_path(str(Path(__file__).parents[1] / "examples/accc_k201_offline.py"))
    return module["build_demo"]()


def test_real_core_preflight_and_reproducible_receipt(demo):
    host, request = demo
    first = host.compose(request)
    assert first.status == "READY"
    assert first == host.compose(request)
    assert first.receipt["skill:inspect"]
    assert first.receipt["evidence:observation-1"]
    assert host.skills.runtime.all_audits() == []
    host.binding.record.reference = host.binding.record.reference.model_copy(
        update={"record_version": "2"}
    )
    assert first.manifest_hash != host.compose(request).manifest_hash


@pytest.mark.parametrize(
    "field",
    [
        "tenant_id",
        "actor_id",
        "roles",
        "authorization_valid",
        "receipt_context",
        "actions",
        "verified_evidence_types",
    ],
)
def test_client_authority_rejected(demo, field):
    _, request = demo
    with pytest.raises(ValueError):
        CompositionRequest.model_validate({**request.model_dump(), field: "forged"})


@pytest.mark.parametrize(
    "principal",
    [
        ActorContext("user", {"engineer"}, "other"),
        ActorContext("", {"engineer"}, "synthetic"),
        ActorContext("user", set(), "synthetic"),
        None,
    ],
)
def test_invalid_host_identity_never_reads_source(demo, principal):
    host, request = demo
    host.authenticate = lambda: principal
    assert host.compose(request).status == "BLOCKED"
    assert host.binding.calls == 0


def test_revoked_policy_rechecked_without_cached_admission(demo):
    host, request = demo
    assert host.compose(request).status == "READY"
    host.skills.runtime.policy_engine.policies["engineer"]["functions"] = []
    assert host.compose(request).status == "BLOCKED"
    assert host.binding.calls == 1


def test_object_sharing_denial_precedes_source_access(demo):
    host, request = demo
    runtime = host.skills.runtime
    obj = runtime.get_object("K-201")
    obj.properties["sharingScope"] = "restricted"
    runtime.upsert_object(obj)
    assert host.compose(request).status == "BLOCKED"
    assert host.binding.calls == 0


def test_evidence_permission_revoked_prevents_source_read(demo):
    host, request = demo
    host.skills.runtime.policy_engine.policies["engineer"]["read_types"].remove("vibration")
    assert host.compose(request).status == "BLOCKED"
    assert host.binding.calls == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("tenant_id", "other"),
        ("subject_id", "other"),
        ("evidence_type", "other"),
        ("observed_at", "2026-11-03T13:00:00+00:00"),
        ("observed_at", "2026-11-03T12:00:00"),
        ("payload_hash", ""),
    ],
)
def test_source_scope_and_time_fail_closed(demo, field, value):
    host, request = demo
    host.binding.record.evidence[field] = value
    assert host.compose(request).status == "BLOCKED"


def test_stale_evidence_abstains(demo):
    host, request = demo
    now = host.clock()
    host.clock = lambda: now + timedelta(seconds=61)
    result = host.compose(request)
    assert result.status == "NEEDS_EVIDENCE"
    assert not result.skill_ids


def test_conflict_abstains(demo):
    host, request = demo
    host.binding.record.evidence["conflict"] = True
    assert "SOURCE_CONFLICT" in host.compose(request).blockers


def test_unknown_method_combination_blocks(demo):
    host, request = demo
    host.profile = replace(host.profile, compatible_sets=frozenset())
    assert host.compose(request).blockers == ["METHOD_INCOMPATIBLE"]
    assert host.binding.calls == 0


@pytest.mark.parametrize("change", ["unqualified", "modified", "action", "missing", "preflight"])
def test_skill_failures_never_admit(demo, change):
    host, request = demo
    spec = host.skills.get("inspect").model_copy(deep=True)
    if change == "unqualified":
        host.profile = replace(host.profile, skill_hashes={})
    elif change == "modified":
        spec.binding_id = "unqualified-revision"
    elif change == "missing":
        host.skills._skills.clear()
    elif change == "action":
        spec.authority.execute_actions.add("UnauthorizedAction")
        host.profile = replace(host.profile, skill_hashes={"inspect": contract_hash(spec)})
    else:
        host.skills.runtime.type_registry = None
    if change != "missing":
        host.skills.register(spec)
    assert host.compose(request).status == "BLOCKED"
    assert host.binding.calls == 0


def test_adapter_uses_real_sdk_without_model(demo):
    pytest.importorskip("agent_framework")
    from cepio.integrations.microsoft.accc import composition_tool

    host, request = demo
    tool = composition_tool(host)
    assert tool.approval_mode == "always_require"
    result = asyncio.run(tool.invoke(arguments=request.model_dump(mode="json")))
    assert json.loads(result[0].text)["status"] == "READY"


@pytest.mark.parametrize(
    "failure",
    [
        "binding",
        "missing_capability",
        "changed_capability",
        "clock",
        "freshness",
        "missing_evidence",
    ],
)
def test_host_configuration_and_source_failure(demo, failure):
    host, request = demo
    if failure == "binding":
        host.registration = host.registration.model_copy(update={"status": "degraded"})
    elif failure == "missing_capability":
        host.registry.capabilities.clear()
    elif failure == "changed_capability":
        host.registry.capabilities[0].version = "changed"
    elif failure == "clock":
        now = host.clock().replace(tzinfo=None)
        host.clock = lambda: now
    else:
        item = host.profile.evidence[0]
        item = replace(
            item,
            **({"max_age_seconds": 0} if failure == "freshness" else {"external_id": "missing"}),
        )
        host.profile = replace(host.profile, evidence=(item,))
    result = host.compose(request)
    assert result.status == ("NEEDS_EVIDENCE" if failure == "missing_evidence" else "BLOCKED")
    assert not result.skill_ids


def test_http_binding_validates_signed_token_and_rejects_wrong_tenant(demo, monkeypatch):
    import time
    from types import SimpleNamespace
    import jwt
    from cryptography.hazmat.primitives.asymmetric import rsa
    from fastapi.security import HTTPAuthorizationCredentials
    from starlette.requests import Request
    from cepio.accc_runtime_binding import AuthenticatedReadOnlyComposer

    host, request = demo
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setattr(
        jwt.PyJWKClient,
        "get_signing_key_from_jwt",
        lambda self, token: SimpleNamespace(key=key.public_key()),
    )
    for name, value in {
        "CEPIO_AUTH_MODE": "entra",
        "CEPIO_ENVIRONMENT": "test",
        "CEPIO_ENTRA_TENANT_ID": "synthetic",
        "CEPIO_ENTRA_AUDIENCE": "offline",
        "CEPIO_ENTRA_ISSUER": "https://offline.invalid",
        "CEPIO_ENTRA_JWKS_URI": "https://offline.invalid/keys",
    }.items():
        monkeypatch.setenv(name, value)
    for tenant, status in [("synthetic", "READY"), ("other", "BLOCKED")]:
        token = jwt.encode(
            {
                "oid": "engineer",
                "roles": ["engineer"],
                "tid": tenant,
                "aud": "offline",
                "iss": "https://offline.invalid",
                "iat": int(time.time()),
                "exp": int(time.time()) + 60,
            },
            key,
            algorithm="RS256",
        )
        bound = AuthenticatedReadOnlyComposer.from_http_request(
            http_request=Request({"type": "http", "headers": []}),
            credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
            registry=host.registry,
            skills=host.skills,
            binding=host.binding,
            registration=host.registration,
            profile=host.profile,
            clock=host.clock,
        )
        assert bound.compose(request).status == status


def test_optional_adapter_contract_without_sdk(demo, monkeypatch):
    import sys
    from types import SimpleNamespace
    from cepio.integrations.microsoft.accc import composition_tool

    host, request = demo
    registration = {}

    def register(function, **options):
        registration.update(options)
        return function

    monkeypatch.setitem(sys.modules, "agent_framework", SimpleNamespace(tool=register))
    invoke = composition_tool(host)
    assert registration["schema"] is CompositionRequest
    assert registration["approval_mode"] == "always_require"
    assert json.loads(invoke(**request.model_dump()))["status"] == "READY"
    with pytest.raises(ValueError):
        invoke(**request.model_dump(), tenant_id="forged")

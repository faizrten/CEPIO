import httpx
import pytest

from cepio.auth import ActorContext
from cepio.auto_ontology_binding import AutoOntologyReadError, AutoOntologyTermBinding
from cepio.platform_bindings import qualify_evidence_binding, register_evidence_binding


def setup_binding(*, payload=None, status=200, principal=None, authorize=None):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(
            status,
            json=payload
            if payload is not None
            else {"data": {"id": "term-1", "name": "Equipment", "name_certified": True}},
            headers={"location": "https://other.example/secret"},
        )

    client = httpx.Client(transport=httpx.MockTransport(handle), follow_redirects=True)
    binding = AutoOntologyTermBinding(
        origin="https://catalog.example",
        tenant_id="tenant-a",
        actor_id="engineer-a",
        term_ids=frozenset({"term-1"}),
        client=client,
        principal=principal or (lambda: ActorContext("engineer-a", set(), "tenant-a")),
        authorize=authorize or (lambda actor, term: True),
    )
    return binding, requests


def test_contract_preserves_semantic_provenance_without_approval_or_source_version():
    binding, requests = setup_binding()
    registration = register_evidence_binding(binding, capability_id="semantic-inspection")
    assert registration.authority == "observation-only"
    assert not requests  # Registration never reads data.
    result = binding.resolve_evidence("term-1")
    assert result.reference.partition == "tenant-a"
    assert result.reference.record_version is None
    assert len(result.reference.metadata["response_sha256"]) == 64
    assert result.evidence["cepio_status"] == "proposal-only"
    assert result.evidence["evidence_kind"] == "semantic-metadata"
    assert requests[0].method == "GET"
    assert requests[0].url.path == "/api/terms/term-1"
    assert not qualify_evidence_binding(binding, external_id="term-1").versioned


@pytest.mark.parametrize(
    "actor",
    [
        ActorContext("engineer-a", set(), "tenant-b"),
        ActorContext("engineer-b", set(), "tenant-a"),
        ActorContext("engineer-a", set(), None),
    ],
)
def test_wrong_principal_rejected_before_transport(actor):
    binding, requests = setup_binding(principal=lambda: actor)
    with pytest.raises(PermissionError):
        binding.resolve_evidence("term-1")
    assert not requests


def test_permission_revocation_checked_every_call():
    allowed = [True]
    binding, requests = setup_binding(authorize=lambda actor, term: allowed[0])
    binding.resolve_evidence("term-1")
    allowed[0] = False
    with pytest.raises(PermissionError):
        binding.resolve_evidence("term-1")
    assert len(requests) == 1


@pytest.mark.parametrize("term", ["unknown", "../connections", "term-1?tenant=b"])
def test_out_of_scope_terms_never_reach_transport(term):
    binding, requests = setup_binding()
    with pytest.raises(PermissionError):
        binding.resolve_evidence(term)
    assert not requests


@pytest.mark.parametrize("status", [301, 302, 401, 403, 404, 500])
def test_upstream_failure_and_redirect_do_not_leak_response(status):
    binding, requests = setup_binding(status=status, payload={"secret": "do-not-log"})
    with pytest.raises(AutoOntologyReadError) as error:
        binding.resolve_evidence("term-1")
    assert "do-not-log" not in str(error.value)
    assert len(requests) == 1


@pytest.mark.parametrize("payload", [[], {}, {"data": []}, {"data": {"id": "other"}}])
def test_malformed_and_wrong_identity_responses_fail_closed(payload):
    binding, _ = setup_binding(payload=payload)
    with pytest.raises(AutoOntologyReadError):
        binding.resolve_evidence("term-1")


def test_payload_bound():
    binding, _ = setup_binding(payload={"data": {"id": "term-1", "name": "x" * 262144}})
    with pytest.raises(AutoOntologyReadError, match="size limit"):
        binding.resolve_evidence("term-1")


@pytest.mark.parametrize(
    "origin",
    [
        "http://catalog.example",
        "https://user:secret@catalog.example",
        "https://catalog.example/api",
        "https://catalog.example?token=secret",
    ],
)
def test_unsafe_host_configuration_rejected(origin):
    with pytest.raises(ValueError):
        AutoOntologyTermBinding(
            origin=origin,
            tenant_id="t",
            actor_id="a",
            term_ids=frozenset({"term-1"}),
            client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))),
            principal=lambda: ActorContext("a", set(), "t"),
            authorize=lambda actor, term: True,
        )


@pytest.mark.parametrize("failure", ["timeout", "bad-json"])
def test_transport_errors_are_sanitized(failure):
    binding, _ = setup_binding()

    def fail(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("secret-url-token")
        return httpx.Response(200, content=b"secret-not-json")

    binding._client = httpx.Client(transport=httpx.MockTransport(fail))
    with pytest.raises(AutoOntologyReadError) as error:
        binding.resolve_evidence("term-1")
    assert "secret" not in str(error.value)


@pytest.mark.parametrize(
    "tenant,actor,terms",
    [
        ("", "actor", frozenset({"term-1"})),
        ("tenant", "", frozenset({"term-1"})),
        ("tenant", "actor", frozenset()),
        ("tenant", "actor", frozenset({"../escape"})),
    ],
)
def test_missing_identity_and_unsafe_allowlist_rejected(tenant, actor, terms):
    with pytest.raises(ValueError):
        AutoOntologyTermBinding(
            origin="https://catalog.example",
            tenant_id=tenant,
            actor_id=actor,
            term_ids=terms,
            client=httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500))),
            principal=lambda: ActorContext(actor, set(), tenant),
            authorize=lambda actor, term: True,
        )

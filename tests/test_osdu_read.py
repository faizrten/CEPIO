import httpx
import pytest

from cepio.domain_bindings import ExternalRecordReference
from cepio.integrations.osdu_read import OSDUReadError, OSDURecordReader

REF = ExternalRecordReference(source_system="osdu", source_service="osdu_core",
    record_id="test:work-product-component--WellLog:A", record_kind="osdu:wks:work-product-component--WellLog:1.0.0",
    record_version=42, partition="test")
RECORD = {"id": REF.record_id, "kind": REF.record_kind, "version": 42,
          "data": {"Name": "synthetic"}, "acl": {"viewers": ["test"]},
          "legal": {"legaltags": ["synthetic"]}}


def reader(handler, **kwargs):
    return OSDURecordReader("https://osdu.example", "test", lambda: "test-token",
                            transport=httpx.MockTransport(handler), **kwargs)


def test_exact_version_read_preserves_metadata():
    def handle(request):
        assert request.method == "GET"
        assert request.url.path.endswith("/42")
        assert request.headers["data-partition-id"] == "test"
        assert request.headers["authorization"] == "Bearer test-token"
        return httpx.Response(200, json=RECORD)
    assert reader(handle).read(REF) == RECORD


@pytest.mark.parametrize("change", [{"partition": "other"}, {"record_version": None},
    {"source_system": "other"}, {"record_version": "../latest"}])
def test_bad_reference_never_calls_source(change):
    def forbidden(request):
        pytest.fail("source must not be called")
    with pytest.raises(OSDUReadError, match="INVALID_SOURCE_REFERENCE"):
        reader(forbidden).read(REF.model_copy(update=change))


@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 302])
def test_source_failure_sanitized_and_no_redirect(status):
    with pytest.raises(OSDUReadError) as exc:
        reader(lambda r: httpx.Response(status, text="secret",
            headers={"Location": "https://other.example"})).read(REF)
    assert "secret" not in str(exc.value)


@pytest.mark.parametrize("change", [{"id": "other"}, {"version": 43}, {"kind": "other"}])
def test_mismatched_identity_rejected(change):
    with pytest.raises(OSDUReadError, match="SOURCE_IDENTITY_MISMATCH"):
        reader(lambda r: httpx.Response(200, json=RECORD | change)).read(REF)


def test_response_bounded():
    with pytest.raises(OSDUReadError, match="SOURCE_RESPONSE_TOO_LARGE"):
        reader(lambda r: httpx.Response(200, json=RECORD), max_bytes=10).read(REF)


def test_revocation_not_hidden_by_cache():
    responses = iter([200, 403])
    client = reader(lambda r: httpx.Response(next(responses), json=RECORD))
    client.read(REF)
    with pytest.raises(OSDUReadError, match="SOURCE_ACCESS_DENIED"):
        client.read(REF)


@pytest.mark.parametrize("body", [[], {}, {**RECORD, "legal": None}])
def test_malformed_record_rejected(body):
    with pytest.raises(OSDUReadError):
        reader(lambda r: httpx.Response(200, json=body)).read(REF)


def test_timeout_sanitized():
    def timeout(request):
        raise httpx.ReadTimeout("secret", request=request)
    with pytest.raises(OSDUReadError, match="SOURCE_RESPONSE_INVALID"):
        reader(timeout).read(REF)


@pytest.mark.parametrize("endpoint", ["http://osdu.example", "https://user:secret@osdu.example",
    "https://osdu.example?token=secret", "https://osdu.example/#fragment"])
def test_unsafe_endpoint_rejected(endpoint):
    with pytest.raises(ValueError):
        OSDURecordReader(endpoint, "test", lambda: "token")


def test_missing_token_never_calls_source():
    client = OSDURecordReader("https://osdu.example", "test", lambda: "")
    with pytest.raises(OSDUReadError, match="SOURCE_AUTH_REQUIRED"):
        client.read(REF)

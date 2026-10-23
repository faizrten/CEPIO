import importlib.util
from pathlib import Path

import pytest


SPEC = importlib.util.spec_from_file_location(
    "boundary_probe", Path(__file__).resolve().parents[1] / "scripts/check_hosted_boundary.py"
)
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)


class Clock:
    now = 0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def test_transient_mcp_404_requires_three_complete_successful_rounds():
    clock = Clock()
    mcp_calls = []

    def request(path, budget):
        assert 0 < budget <= 10
        if path == "/mcp":
            mcp_calls.append(path)
            return (404, False) if len(mcp_calls) == 1 else (401, True)
        return (200, True) if path.endswith("/health") and path.startswith("/api/") else (401, True)

    probe.wait_for_boundary("https://example.test", probe=request, clock=clock, sleep=clock.sleep)
    assert len(mcp_calls) == 4


def test_persistent_404_fails_at_bounded_deadline():
    clock = Clock()
    with pytest.raises(TimeoutError):
        probe.wait_for_boundary(
            "https://example.test",
            timeout=12,
            interval=5,
            probe=lambda path, budget: (404, False),
            clock=clock,
            sleep=clock.sleep,
        )
    assert clock.now == 12


def test_anonymous_success_fails_immediately_without_retry():
    clock = Clock()
    with pytest.raises(RuntimeError, match="Anonymous protected access"):
        probe.wait_for_boundary(
            "https://example.test",
            probe=lambda path, budget: (200, True),
            clock=clock,
            sleep=clock.sleep,
        )
    assert clock.now == 0


@pytest.mark.parametrize(
    "url",
    [
        "http://example.test",
        "https://u:p@example.test",
        "https://example.test/path",
        "https://example.test?token=x",
    ],
)
def test_origin_validation(url):
    with pytest.raises(ValueError):
        probe.wait_for_boundary(url)


def test_startup_override_does_not_silently_select_rest_only_host():
    assert probe.validate_startup({"appCommandLine": ""}) == "image-default"
    assert (
        probe.validate_startup(
            {"appCommandLine": "uvicorn cepio.host_api:app --host 0.0.0.0 --port 8000"}
        )
        == "host-api-override"
    )
    with pytest.raises(ValueError, match="Unexpected App Service startup override"):
        probe.validate_startup({"appCommandLine": "uvicorn cepio.public_api:app"})


def test_denial_requires_a_bearer_challenge_and_no_redirects_are_followed():
    import urllib.error

    class Opener:
        def __init__(self, status, headers):
            self.status, self.headers = status, headers

        def open(self, request, timeout):
            assert request.get_method() == "POST"
            assert request.data == b"{}"
            assert "Authorization" not in request.headers
            raise urllib.error.HTTPError(
                request.full_url, self.status, "synthetic", self.headers, None
            )

    for status, headers, expected in [
        (401, {"WWW-Authenticate": "Bearer"}, True),
        (401, {}, False),
        (302, {"Location": "/login"}, False),
    ]:
        assert probe.request_status(Opener(status, headers), "https://example.test", "/mcp", 1) == (
            status,
            expected,
        )

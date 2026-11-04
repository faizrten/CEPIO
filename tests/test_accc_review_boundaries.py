"""Offline security review checks, runnable with unittest or the existing pytest CI."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from cepio.accc_runtime_binding import AuthenticatedReadOnlyComposer, contract_hash


class AdmissionReviewTests(unittest.TestCase):
    def setUp(self):
        module = runpy.run_path(str(Path(__file__).parents[1] / "examples/accc_k201_offline.py"))
        self.build_demo = module["build_demo"]

    def test_pinned_unsupported_policy_does_not_read_source(self):
        host, request = self.build_demo()
        capability = host.registry.capabilities[0]
        capability.policy_requirements = {"unsupported-policy"}
        host.profile = replace(
            host.profile, capability_hashes={capability.id: contract_hash(capability)}
        )
        result = host.compose(request)
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(host.binding.calls, 0)
        self.assertEqual(result.receipt, {})

    def test_source_reference_tampering_never_returns_a_ready_receipt(self):
        for field, value in [
            ("source_system", "other-source"),
            ("record_id", "other-record"),
            ("record_kind", "other-kind"),
            ("record_version", " "),
        ]:
            with self.subTest(field=field):
                host, request = self.build_demo()
                host.binding.record.reference = host.binding.record.reference.model_copy(
                    update={field: value}
                )
                result = host.compose(request)
                self.assertEqual(result.status, "BLOCKED")
                self.assertEqual(result.skill_ids, [])
                self.assertEqual(result.receipt, {})

    def test_source_exception_is_redacted(self):
        host, request = self.build_demo()
        detail = "synthetic-private-backend-detail"
        with patch.object(host.binding, "resolve_evidence", side_effect=RuntimeError(detail)):
            result = host.compose(request)
        self.assertEqual(result.status, "BLOCKED")
        self.assertEqual(result.blockers, ["HOST_ADMISSION_UNAVAILABLE"])
        self.assertNotIn(detail, result.model_dump_json())
        self.assertEqual(result.receipt, {})

    def test_same_http_binding_revalidates_expired_credentials(self):
        host, request = self.build_demo()
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        at = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)
        token = jwt.encode(
            {
                "oid": "engineer",
                "roles": ["engineer"],
                "tid": "synthetic",
                "aud": "offline",
                "iss": "https://offline.invalid",
                "iat": int(at.timestamp()),
                "exp": int((at + timedelta(seconds=60)).timestamp()),
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
        environment = {
            "CEPIO_AUTH_MODE": "entra",
            "CEPIO_ENVIRONMENT": "test",
            "CEPIO_ENTRA_TENANT_ID": "synthetic",
            "CEPIO_ENTRA_AUDIENCE": "offline",
            "CEPIO_ENTRA_ISSUER": "https://offline.invalid",
            "CEPIO_ENTRA_JWKS_URI": "https://offline.invalid/keys",
            "CEPIO_GROUP_ROLE_MAP": "{}",
        }
        with (
            patch.dict("os.environ", environment),
            patch.object(
                jwt.PyJWKClient,
                "get_signing_key_from_jwt",
                return_value=SimpleNamespace(key=key.public_key()),
            ),
            patch("jwt.api_jwt.datetime") as token_clock,
        ):
            token_clock.now.return_value = at
            self.assertEqual(bound.compose(request).status, "READY")
            self.assertEqual(host.binding.calls, 1)
            token_clock.now.return_value = at + timedelta(seconds=61)
            result = bound.compose(request)
            self.assertEqual(result.status, "BLOCKED")
            self.assertEqual(host.binding.calls, 1)
            self.assertEqual(result.receipt, {})


if __name__ == "__main__":
    unittest.main()

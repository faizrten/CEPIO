"""Native verifier positive/tamper controls using a pinned PUBLIC release bundle."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    directory = Path(os.environ["RUNNER_TEMP"]) / "cepio-cosign"
    binary, bundle = directory / "cosign", directory / "release.sigstore.json"
    identity = "keyless@projectsigstore.iam.gserviceaccount.com"
    issuer = "https://accounts.google.com"
    report = {"qualified": False, "tests": {}}
    base = [str(binary), "verify-blob", "--bundle", str(bundle)]
    with tempfile.TemporaryDirectory(prefix="cepio-verify-") as temporary:
        altered = Path(temporary) / "altered"
        shutil.copyfile(binary, altered)
        with altered.open("ab") as stream:
            stream.write(b"tampered")
        for name, target, cert_identity, cert_issuer, expected in [
            ("valid_public_release", binary, identity, issuer, True),
            ("tampered_blob", altered, identity, issuer, False),
            ("wrong_identity", binary, "wrong@example.invalid", issuer, False),
            ("wrong_issuer", binary, identity, "https://wrong.example.invalid", False),
        ]:
            try:
                result = subprocess.run(
                    base
                    + [
                        "--certificate-identity",
                        cert_identity,
                        "--certificate-oidc-issuer",
                        cert_issuer,
                        str(target),
                    ],
                    capture_output=True,
                    timeout=180,
                    check=False,
                )
                report["tests"][name] = (result.returncode == 0) is expected
            except (OSError, subprocess.TimeoutExpired):
                report["tests"][name] = False
    report["qualified"] = all(report["tests"].values())
    path = Path("evidence/cosign-verifier")
    path.mkdir(parents=True, exist_ok=True)
    report["limits"] = (
        "Public upstream release fixture; no CEPIO OIDC/signing, registry access, deployment or inference. Production requires the exact CEPIO workflow identity, issuer, source/ref/trigger and image binding."
    )
    (path / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Install one checksum-pinned official verifier into runner-local temporary storage."""

import argparse
import hashlib
import os
from pathlib import Path
import platform
import urllib.request


VERSION = "v3.1.4"
BASE = f"https://github.com/sigstore/cosign/releases/download/{VERSION}/"
HASHES = {
    "cosign-linux-amd64": "424e2c97d0b45fd7a6b608a87f090f35633f4c23ece5f092d48bba11aaf4bbfa",
    "cosign-linux-amd64.sigstore.json": "355244bb0186e950ced20f03106640ba3a4630e1223d0467ff34bcebe10bb18a",
}


def download(name, path):
    if name not in HASHES:
        raise ValueError("UNPINNED_TOOL_ASSET")
    with urllib.request.urlopen(BASE + name, timeout=60) as response:
        data = response.read(150 * 1024 * 1024 + 1)
    if hashlib.sha256(data).hexdigest() != HASHES[name]:
        raise ValueError("TOOL_CHECKSUM_MISMATCH")
    path.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-bundle", action="store_true")
    args = parser.parse_args()
    if platform.system() != "Linux" or platform.machine() not in {"x86_64", "amd64"}:
        raise ValueError("UNSUPPORTED_VERIFIER_PLATFORM")
    directory = Path(os.environ["RUNNER_TEMP"]) / "cepio-cosign"
    directory.mkdir(parents=True, exist_ok=True)
    binary = directory / "cosign"
    download("cosign-linux-amd64", binary)
    binary.chmod(0o755)
    if args.release_bundle:
        download("cosign-linux-amd64.sigstore.json", directory / "release.sigstore.json")
    with open(os.environ["GITHUB_PATH"], "a", encoding="utf-8") as stream:
        stream.write(str(directory) + "\n")
    print(f"Pinned Cosign {VERSION}: SHA256 verified")


if __name__ == "__main__":
    main()

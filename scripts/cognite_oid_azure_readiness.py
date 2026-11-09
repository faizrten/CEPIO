"""Read-only verification of existing Azure landing-zone resources.

This script uses the already-configured GitHub-to-Azure OIDC session.
No secrets, resource payloads, subscription IDs or raw CLI errors are emitted.
A failed query means 'not-verified', not that an Azure resource does not exist.
"""

from __future__ import annotations

import json
import subprocess
from typing import Callable


RESOURCE_GROUP = "cepio-labs-rg"
CONTAINER_ENV = "cepio-labs-internal"
REGISTRY = "cepiolabsb5ufvcwpcpcdw"
VAULT = "cepiolabs-b5ufvcwpcpcdw"


def run_check(arguments: list[str]) -> bool:
    try:
        result = subprocess.run(
            ["az", *arguments, "--query", "id", "--output", "tsv"],
            capture_output=True,
            text=True,
            timeout=25,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def collect_readiness(verify: Callable[[list[str]], bool] = run_check) -> dict[str, object]:
    """Probe exact resource names from CEPIO-Labs IaC; never grant permissions."""
    checks = {
        "labs_rg": verify(["group", "show", "--name", RESOURCE_GROUP]),
        "container_apps_environment": verify(
            ["containerapp", "env", "show", "--resource-group", RESOURCE_GROUP, "--name", CONTAINER_ENV]
        ),
        "container_registry": verify(
            ["acr", "show", "--resource-group", RESOURCE_GROUP, "--name", REGISTRY]
        ),
        "key_vault_metadata": verify(["keyvault", "show", "--name", VAULT]),
    }
    return {
        "status": "existing-resources-visible" if all(checks.values()) else "review-azure-access",
        "checks": {
            key: "visible" if value else "not-verified" for key, value in checks.items()
        },
        "identity_scope_qualified": False,
        "blob_container_qualified": False,
        "source_secret_transferred": False,
        "azure_resources_modified": False,
    }


def main() -> int:
    report = collect_readiness()
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "existing-resources-visible" else 3


if __name__ == "__main__":
    raise SystemExit(main())

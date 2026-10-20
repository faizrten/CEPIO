from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def require(text: str, needle: str, source: str) -> None:
    if needle not in text:
        raise SystemExit(f"{source} missing required deployment invariant: {needle}")


def main() -> int:
    dockerfile = (ROOT / "Dockerfile").read_text()
    appservice = (ROOT / "deploy/appservice/main.bicep").read_text()
    search = (ROOT / "deploy/search/main.bicep").read_text()
    aks_text = (ROOT / "deploy/aks/cepio.yaml").read_text()

    require(dockerfile, "cepio.public_api:app", "Dockerfile")
    require(dockerfile, "USER cepio", "Dockerfile")
    require(appservice, "/api/v1/health", "App Service profile")
    require(appservice, "SystemAssigned", "App Service profile")
    require(appservice, "CEPIO_AUTH_MODE', value: 'entra'", "App Service profile")
    require(
        appservice,
        "WEBSITES_ENABLE_APP_SERVICE_STORAGE', value: 'true'",
        "App Service profile",
    )
    require(appservice, "sqlite:////home/data/cepio.db", "App Service profile")
    require(appservice, "capacity: 1", "App Service profile")
    require(appservice, "minTlsVersion: '1.2'", "App Service profile")
    require(search, "disableLocalAuth: true", "Azure AI Search profile")
    require(search, "name: 'basic'", "Azure AI Search profile")
    require(search, "principalId: appServicePrincipalId", "Azure AI Search profile")
    for role_id in (
        "7ca78c08-252a-4471-8644-bb5ff32d4ba0",
        "8ebe5a00-799e-43f5-93ac-243d3dce84a7",
        "1407120a-92aa-4202-b7e9-c0e197c71c8f",
    ):
        require(search, role_id, "Azure AI Search RBAC")
    require(aks_text, "/api/v1/health", "AKS profile")
    require(aks_text, "azure.workload.identity/use", "AKS profile")
    require(aks_text, 'CEPIO_AUTH_MODE, value: "entra"', "AKS profile")

    documents = list(yaml.safe_load_all(aks_text))
    deployment = next(d for d in documents if d and d.get("kind") == "Deployment")
    if deployment["spec"]["replicas"] != 1:
        raise SystemExit("Reference SQLite AKS deployment must remain single-replica")

    pvc = next(d for d in documents if d and d.get("kind") == "PersistentVolumeClaim")
    if pvc["spec"]["accessModes"] != ["ReadWriteOnce"]:
        raise SystemExit("Reference SQLite PVC must be ReadWriteOnce")

    print("CEPIO deployment profiles OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

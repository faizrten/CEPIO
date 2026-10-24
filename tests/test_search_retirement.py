"""Retired Azure Search is not an active CEPIO runtime dependency."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_retired_search_provider_not_in_runtime_or_ci():
    for path in (
        "src/cepio/azure_search.py",
        "scripts/run_azure_search_scale_qualification.py",
        "tests/test_azure_search_adapter.py",
        ".github/workflows/azure-search-adapter.yml",
        ".github/workflows/azure-search-scale.yml",
    ):
        assert not (ROOT / path).exists(), f"Retired provider still active: {path}"


def test_runtime_package_excludes_retired_search_sdk():
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "azure-search-documents" not in project
    assert "azure-search =" not in project
    assert "azure-search" not in (ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_deployment_clears_stale_search_app_settings():
    workflow = (ROOT / ".github/workflows/deploy-azure.yml").read_text(encoding="utf-8")
    builder = (ROOT / "scripts/build_demo_image.py").read_text(encoding="utf-8")
    bicep = (ROOT / "deploy/appservice/main.bicep").read_text(encoding="utf-8")
    assert "scripts/build_demo_image.py" in workflow
    assert "CEPIO_RUNTIME_EXTRAS=mcp" in builder
    assert "az webapp config appsettings delete" in workflow
    assert "--setting-names CEPIO_AZURE_SEARCH_ENDPOINT CEPIO_AZURE_SEARCH_INDEX" in workflow
    assert "az webapp config appsettings set" not in workflow
    assert "azureSearchEndpoint" not in bicep
    assert "CEPIO_AZURE_SEARCH_ENDPOINT" not in bicep

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def workflow():
    path = ROOT / ".github" / "workflows" / "deploy-azure.yml"
    return yaml.load(path.read_text(), Loader=yaml.BaseLoader)


def test_deployment_requires_successful_main_push_ci(workflow):
    assert workflow["on"] == {
        "workflow_run": {
            "workflows": ["CEPIO CI"],
            "types": ["completed"],
            "branches": ["main"],
        }
    }
    ci = yaml.load(
        (ROOT / ".github" / "workflows" / "ci.yml").read_text(),
        Loader=yaml.BaseLoader,
    )
    assert ci["name"] == "CEPIO CI"
    assert " ".join(workflow["jobs"]["deploy"]["if"].split()) == (
        "github.event.workflow_run.conclusion == 'success' && "
        "github.event.workflow_run.event == 'push' && "
        "github.event.workflow_run.head_branch == 'main' && "
        "github.event.workflow_run.head_repository.full_name == github.repository"
    )


def test_deployment_uses_environment_scoped_oidc(workflow):
    deploy = workflow["jobs"]["deploy"]
    assert deploy["environment"] == "azure-demo"
    assert workflow["permissions"] == {"contents": "read"}
    assert deploy["permissions"] == {"contents": "read", "id-token": "write"}
    login = next(step for step in deploy["steps"] if step.get("uses") == "azure/login@v2")
    assert login["with"] == {
        "client-id": "${{ vars.AZURE_CLIENT_ID }}",
        "tenant-id": "${{ vars.AZURE_TENANT_ID }}",
        "subscription-id": "${{ vars.AZURE_SUBSCRIPTION_ID }}",
    }
    assert "secrets." not in str(deploy)


def test_deployment_checks_out_tested_commit_without_saved_credentials(workflow):
    deploy = workflow["jobs"]["deploy"]
    checkout = deploy["steps"][0]
    assert checkout["uses"] == "actions/checkout@v4"
    assert checkout["with"] == {
        "ref": "${{ github.event.workflow_run.head_sha }}",
        "persist-credentials": "false",
    }
    assert deploy["env"]["DEPLOY_SHA"] == "${{ github.event.workflow_run.head_sha }}"
    assert workflow["concurrency"] == {
        "group": "cepio-azure-demo",
        "cancel-in-progress": "false",
    }
    steps = deploy["steps"]
    guard = next(i for i, step in enumerate(steps) if step.get("name") == "Reject superseded commits")
    login = next(i for i, step in enumerate(steps) if step.get("uses") == "azure/login@v2")
    assert guard < login
    assert '[[ "$main_sha" != "$DEPLOY_SHA" ]]' in steps[guard]["run"]
    assert "exit 1" in steps[guard]["run"]


def test_deployment_pins_built_image_digest(workflow):
    steps = workflow["jobs"]["deploy"]["steps"]
    build = next(step for step in steps if step.get("id") == "build")["run"]
    deploy = next(step for step in steps if step.get("name") == "Deploy immutable image")
    assert "${DEPLOY_SHA}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" in build
    assert "--no-logs" in build
    assert "sha256:[0-9a-f]{64}" in build
    assert 'image=${server}/cepio@${digest}' in build
    assert deploy["env"]["IMAGE"] == "${{ steps.build.outputs.image }}"
    assert '--container-image-name "$IMAGE"' in deploy["run"]
    assert '[[ "$configured" != "DOCKER|$IMAGE" ]]' in deploy["run"]


def test_deployment_checks_health_and_anonymous_read_denial(workflow):
    steps = workflow["jobs"]["deploy"]["steps"]
    verify = steps[-1]["run"]
    assert "/api/v1/health" in verify
    assert 'data.get("status") == "ok"' in verify
    assert "/api/v1/objects" in verify
    assert '[[ "$status" != "401" ]]' in verify
    assert "GITHUB_STEP_SUMMARY" in verify

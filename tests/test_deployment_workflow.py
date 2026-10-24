from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
AZURE_LOGIN = "azure/login@7184910d9eb2b1c5e48f7073824a90609bb9b6d6"


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
    login = next(step for step in deploy["steps"] if step.get("uses") == AZURE_LOGIN)
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
        "ref": "refs/heads/main",
        "persist-credentials": "false",
    }
    assert deploy["env"]["DEPLOY_SHA"] == "${{ github.event.workflow_run.head_sha }}"
    assert workflow["concurrency"] == {
        "group": "cepio-azure-demo",
        "cancel-in-progress": "false",
    }
    steps = deploy["steps"]
    guard = next(
        i for i, step in enumerate(steps) if step.get("name") == "Reject superseded commits"
    )
    login = next(i for i, step in enumerate(steps) if step.get("uses") == AZURE_LOGIN)
    assert guard < login
    assert 'checked_out_sha="$(git rev-parse HEAD)"' in steps[guard]["run"]
    assert (
        '[[ "$checked_out_sha" != "$DEPLOY_SHA" || "$main_sha" != "$DEPLOY_SHA" ]]'
        in steps[guard]["run"]
    )
    assert "exit 1" in steps[guard]["run"]


def test_deployment_pins_built_image_digest(workflow):
    steps = workflow["jobs"]["deploy"]["steps"]
    build = next(step for step in steps if step.get("id") == "build")["run"]
    deploy = next(step for step in steps if step.get("name") == "Deploy immutable image")
    assert build == "python3 scripts/build_demo_image.py"
    # The helper's functional tests reject wrong source/run/attempt tags and
    # registry digests and withhold outputs on signing/verification failure.
    assert deploy["env"]["IMAGE"] == "${{ steps.build.outputs.image }}"
    assert '--container-image-name "$IMAGE"' in deploy["run"]
    assert '[[ "$configured" != "DOCKER|$IMAGE" ]]' in deploy["run"]


def test_deployment_checks_health_and_anonymous_read_denial(workflow):
    steps = workflow["jobs"]["deploy"]["steps"]
    verify = steps[-1]["run"]
    assert 'scripts/check_hosted_boundary.py --base-url "https://$host"' in verify
    assert "GITHUB_STEP_SUMMARY" in verify
    startup = next(
        step for step in steps if step.get("name") == "Verify hosted startup before deployment"
    )
    assert "appCommandLine:appCommandLine" in startup["run"]
    assert "--startup-config" in startup["run"]
    build = next(i for i, step in enumerate(steps) if step.get("id") == "build")
    assert steps.index(startup) < build


def test_readonly_proof_reuses_existing_identity_and_only_lists_mcp_tools():
    readonly = yaml.load(
        (ROOT / ".github/workflows/api-readonly-access.yml").read_text(),
        Loader=yaml.BaseLoader,
    )
    job = readonly["jobs"]["check"]
    assert job["if"] == "github.ref == 'refs/heads/main'"
    assert job["environment"] == "azure-demo"
    assert job["permissions"] == {"contents": "read", "id-token": "write"}
    run = job["steps"][-1]["run"]
    assert run == "python3 scripts/check_authenticated_host.py"
    assert job["steps"][-1]["env"]["OIDC_CLIENT_ID"] == "${{ vars.AZURE_CLIENT_ID }}"
    source = (ROOT / "scripts/check_authenticated_host.py").read_text()
    assert '"method": "initialize"' in source
    assert '"method": "tools/list"' in source
    assert '"method": "tools/call"' not in source
    assert '"GET"' in source
    assert '"POST"' not in source
    compile(source, "check_authenticated_host.py", "exec")

"""Build and attest only the current main demo source before App Service mutation."""

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from check_deployed_image import command
from image_provenance import statement, hosted_runner, verify, IMAGE, REPO


def clean_source(source):
    if (
        not re.fullmatch(r"[0-9a-f]{40}", source)
        or command(["git", "rev-parse", "HEAD"]).strip() != source
    ):
        raise ValueError("SOURCE_CHANGED")
    if (
        command(["git", "status", "--porcelain", "--untracked-files=all"]).strip()
        or command(["git", "ls-files", "--others", "--ignored", "--exclude-standard"]).strip()
    ):
        raise ValueError("BUILD_CONTEXT_NOT_CLEAN")


def main():
    source = os.environ["DEPLOY_SHA"]
    run_id = os.environ["GITHUB_RUN_ID"]
    attempt = os.environ["GITHUB_RUN_ATTEMPT"]
    if (
        os.environ.get("GITHUB_REPOSITORY") != REPO
        or os.environ.get("GITHUB_REF") != "refs/heads/main"
        or os.environ.get("GITHUB_EVENT_NAME") != "workflow_dispatch"
        or os.environ.get("GITHUB_SHA") != source
    ):
        raise ValueError("UNEXPECTED_BUILD_CONTEXT")
    if os.environ.get("AZURE_CONTAINER_REGISTRY") != "cepiodemo31d48":
        raise ValueError("UNEXPECTED_REGISTRY")
    if not all(re.fullmatch(r"[1-9][0-9]*", v) for v in [run_id, attempt]):
        raise ValueError("INVALID_BUILD_ID")
    clean_source(source)
    run = json.loads(command(["gh", "api", f"repos/{REPO}/actions/runs/{run_id}"]))
    if (
        str(run.get("id")) != run_id
        or str(run.get("run_attempt")) != attempt
        or run.get("head_sha") != source
        or run.get("head_branch") != "main"
        or run.get("path") != ".github/workflows/deploy-azure.yml"
        or run.get("repository", {}).get("full_name") != REPO
        or run.get("event") != "workflow_dispatch"
        or run.get("status") != "in_progress"
    ):
        raise ValueError("UNEXPECTED_BUILD_RUN")
    hosted_runner(run_id, command)
    evidence = Path(os.environ["RUNNER_TEMP"]) / "cepio-provenance"
    evidence.mkdir(parents=True, exist_ok=True)
    archive = Path(os.environ["RUNNER_TEMP"]) / "cepio-clean-source.tar"
    command(["git", "archive", "--format=tar", "--output", str(archive), source])
    with archive.open("rb") as stream:
        archive_sha = hashlib.file_digest(stream, "sha256").hexdigest()
    materials = {
        "source_archive_sha256": archive_sha,
        "dockerfile_sha256": hashlib.sha256(Path("Dockerfile").read_bytes()).hexdigest(),
        "dockerignore_sha256": hashlib.sha256(Path(".dockerignore").read_bytes()).hexdigest(),
    }
    tag = f"cepio:{source}-{run_id}-{attempt}"
    built = json.loads(
        command(
            [
                "az",
                "acr",
                "build",
                "--registry",
                "cepiodemo31d48",
                "--image",
                tag,
                "--file",
                "Dockerfile",
                "--build-arg",
                "CEPIO_RUNTIME_EXTRAS=mcp",
                "--no-logs",
                "--output",
                "json",
                ".",
            ],
            timeout=1200,
        )
    )
    acr_id = built.get("runId", "")
    if not re.fullmatch(r"[a-z0-9]{1,64}", acr_id):
        raise ValueError("INVALID_ACR_RUN")
    acr = json.loads(
        command(
            [
                "az",
                "acr",
                "task",
                "show-run",
                "--registry",
                "cepiodemo31d48",
                "--run-id",
                acr_id,
                "--output",
                "json",
                "--only-show-errors",
            ]
        )
    )
    digest = command(
        [
            "az",
            "acr",
            "repository",
            "show",
            "--name",
            "cepiodemo31d48",
            "--image",
            tag,
            "--query",
            "digest",
            "--output",
            "tsv",
        ]
    ).strip()
    clean_source(source)
    item = statement(run, acr, source, digest, materials)
    image = IMAGE + "@" + digest
    (evidence / "provenance.json").write_text(json.dumps(item, indent=2) + "\n")
    (evidence / "predicate.json").write_text(json.dumps(item["predicate"], indent=2) + "\n")
    with tempfile.TemporaryDirectory(prefix="cepio-sign-") as directory:
        old_config = os.environ.get("DOCKER_CONFIG")
        os.environ["DOCKER_CONFIG"] = directory
        try:
            credential = json.loads(
                command(
                    [
                        "az",
                        "acr",
                        "login",
                        "--name",
                        "cepiodemo31d48",
                        "--expose-token",
                        "--output",
                        "json",
                        "--only-show-errors",
                    ]
                )
            )
            command(
                [
                    "docker",
                    "--config",
                    directory,
                    "login",
                    IMAGE.split("/", 1)[0],
                    "--username",
                    "00000000-0000-0000-0000-000000000000",
                    "--password-stdin",
                ],
                stdin=credential["accessToken"],
            )
            del credential
            # Same existing identity/repository. No keys, role grants, GitHub
            # attestation API or cross-run Actions artifact download permission.
            command(
                [
                    "cosign",
                    "attest",
                    "--yes",
                    "--oidc-provider",
                    "github-actions",
                    "--type",
                    "slsaprovenance1",
                    "--predicate",
                    str(evidence / "predicate.json"),
                    "--bundle",
                    str(evidence / "provenance.sigstore.json"),
                    image,
                ],
                timeout=180,
            )
            verify(image, source, run, acr, evidence, command)
        finally:
            if old_config is None:
                os.environ.pop("DOCKER_CONFIG", None)
            else:
                os.environ["DOCKER_CONFIG"] = old_config
    # These outputs exist only after signing and independent registry verification.
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as stream:
        stream.write(f"image={image}\nserver={IMAGE.split('/', 1)[0]}\n")
    print(
        json.dumps(
            {
                "source_sha": source,
                "image": image,
                "acr_run_id": acr_id,
                "signed_provenance": "verified",
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, AttributeError):
        raise SystemExit("BUILD_OR_PROVENANCE_FAILED; deployment outputs withheld") from None

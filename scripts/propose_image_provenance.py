"""Construct an UNSIGNED, review-only exact-image provenance proposal. No network/signing."""

import re


REPO = "faizrten/CEPIO"
IMAGE = "cepiodemo31d48.azurecr.io/cepio"
WORKFLOW = "https://github.com/" + REPO + "/.github/workflows/deploy-azure.yml"
BUILD_TYPE = WORKFLOW + "/acr-orchestration/v1"


def proposal(run, acr, source, digest, context_sha256, dockerfile_sha256, *, expected_event="workflow_run"):
    """Inputs must be collected by the future build job, never supplied by a caller."""
    if not re.fullmatch(r"[0-9a-f]{40}", source) or not re.fullmatch(
        r"sha256:[0-9a-f]{64}", digest
    ):
        raise ValueError("INVALID_SUBJECT_OR_SOURCE")
    if not all(re.fullmatch(r"[0-9a-f]{64}", x) for x in (context_sha256, dockerfile_sha256)):
        raise ValueError("INVALID_MATERIAL_HASH")
    run_id, attempt = str(run.get("id", "")), str(run.get("run_attempt", ""))
    acr_id = acr.get("runId", "")
    if not (
        re.fullmatch(r"[1-9][0-9]*", run_id)
        and re.fullmatch(r"[1-9][0-9]*", attempt)
        and re.fullmatch(r"[a-z0-9]{1,64}", acr_id)
    ):
        raise ValueError("INVALID_BUILD_ID")
    if not (
        run.get("head_sha") == source
        and run.get("head_branch") == "main"
        and expected_event in {"workflow_run", "workflow_dispatch"}
        and run.get("event") == expected_event
        and run.get("path") == ".github/workflows/deploy-azure.yml"
        and run.get("repository", {}).get("full_name") == REPO
        and (
            (run.get("status"), run.get("conclusion"))
            in {("in_progress", None), ("completed", "success")}
        )
        and acr.get("status") == "Succeeded"
        and any(
            x.get("registry") == IMAGE.split("/", 1)[0]
            and x.get("repository") == "cepio"
            and x.get("digest") == digest
            and x.get("tag") == f"{source}-{run_id}-{attempt}"
            for x in acr.get("outputImages", [])
        )
    ):
        raise ValueError("BUILD_SOURCE_OR_IMAGE_MISMATCH")
    predicate = {
        "buildDefinition": {
            "buildType": BUILD_TYPE,
            "externalParameters": {"sourceRef": "refs/heads/main", "runtimeExtras": "mcp"},
            "resolvedDependencies": [
                {"uri": "git+https://github.com/" + REPO, "digest": {"gitCommit": source}},
                {"uri": "build-context.tar", "digest": {"sha256": context_sha256}},
                {"uri": "Dockerfile", "digest": {"sha256": dockerfile_sha256}},
            ],
        },
        "runDetails": {
            "builder": {"id": WORKFLOW + "@refs/heads/main"},
            "metadata": {
                "invocationId": f"https://github.com/{REPO}/actions/runs/{run_id}/attempts/{attempt}"
            },
            "byproducts": [{"name": "acr-run-id", "content": acr_id}],
        },
    }
    return {
        "status": "UNSIGNED_PROPOSAL_NOT_EVIDENCE",
        "activation_requires_separate_permission_review": True,
        "statement": {
            "_type": "https://in-toto.io/Statement/v1",
            "subject": [{"name": IMAGE, "digest": {"sha256": digest.removeprefix("sha256:")}}],
            "predicateType": "https://slsa.dev/provenance/v1",
            "predicate": predicate,
        },
        "limits": "GitHub orchestration of a remote ACR build; not an ACR-signed builder statement or a SLSA level claim. Material hashes require build-time capture of the actual submitted bytes.",
    }

"""Exact-image, existing-OIDC Cosign provenance; no GitHub permission expansion."""

import base64
import json
from pathlib import Path
import re

from propose_image_provenance import proposal, IMAGE, REPO, WORKFLOW


PREDICATE = "https://slsa.dev/provenance/v1"
BUILD_TYPE = WORKFLOW + "/acr-orchestration/v2"
MATERIALS = ("source_archive_sha256", "dockerfile_sha256", "dockerignore_sha256")


def statement(run, acr, source, digest, materials):
    if set(materials) != set(MATERIALS) or not all(
        isinstance(materials[k], str) and re.fullmatch(r"[0-9a-f]{64}", materials[k])
        for k in MATERIALS
    ):
        raise ValueError("INVALID_PROVENANCE_MATERIALS")
    result = proposal(run, acr, source, digest, materials[MATERIALS[0]], materials[MATERIALS[1]],
                      expected_event="workflow_dispatch")[
        "statement"
    ]
    definition = result["predicate"]["buildDefinition"]
    definition["buildType"] = BUILD_TYPE
    definition["externalParameters"]["contextPolicy"] = "clean-git-worktree-with-dockerignore"
    definition["resolvedDependencies"][1]["uri"] = "clean-git-source.tar"
    definition["resolvedDependencies"].append(
        {"uri": ".dockerignore", "digest": {"sha256": materials[MATERIALS[2]]}}
    )
    # SLSA ResourceDescriptor.content is base64 bytes, not a plain run ID.
    result["predicate"]["runDetails"]["byproducts"] = [
        {"name": "acr-build", "uri": "azure-acr://cepiodemo31d48/runs/" + acr["runId"]}
    ]
    return result


def hosted_runner(run_id, execute):
    jobs = json.loads(
        execute(["gh", "api", f"repos/{REPO}/actions/runs/{run_id}/jobs?filter=latest&per_page=100"])
    )
    matches = [j for j in jobs.get("jobs", []) if j.get("name") == "deploy"]
    validation = {
        "validate / " + name for name in (
            "ci-unit", "ci-contracts", "ci-drilling", "ci-refinery",
            "ci-package", "ci-container", "test",
        )
    }
    entries = jobs.get("jobs", [])
    if (
        len(matches) != 1
        or jobs.get("total_count") != len(entries)
        or len(entries) != len(validation) + 1
        or {j.get("name") for j in entries} != validation | {"deploy"}
        or any(
            j.get("status") != "completed" or j.get("conclusion") != "success"
            for j in entries if j.get("name") in validation
        )
    ):
        raise ValueError("UNEXPECTED_PROVENANCE_RUNNER")
    job = matches[0]
    if (
        job.get("runner_group_name") != "GitHub Actions"
        or "ubuntu-latest" not in job.get("labels", [])
        or "self-hosted" in job.get("labels", [])
    ):
        raise ValueError("UNEXPECTED_PROVENANCE_RUNNER")


def verify_command(image, source):
    if not re.fullmatch(re.escape(IMAGE) + r"@sha256:[0-9a-f]{64}", image) or not re.fullmatch(
        r"[0-9a-f]{40}", source
    ):
        raise ValueError("INVALID_PROVENANCE_TARGET")
    return [
        "cosign",
        "verify-attestation",
        "--type",
        "slsaprovenance1",
        "--check-claims=true",
        "--output",
        "json",
        "--certificate-identity",
        WORKFLOW + "@refs/heads/main",
        "--certificate-oidc-issuer",
        "https://token.actions.githubusercontent.com",
        "--certificate-github-workflow-sha",
        source,
        "--certificate-github-workflow-ref",
        "refs/heads/main",
        "--certificate-github-workflow-repository",
        REPO,
        "--certificate-github-workflow-trigger",
        "workflow_dispatch",
        image,
    ]


def verified_statement(output, run, acr, source, digest):
    # Only feed successful cosign verify-attestation stdout here, never a raw
    # registry envelope. Cosign may emit one JSON object per line or an array.
    if len(output) > 2 * 1024 * 1024:
        raise ValueError("PROVENANCE_OUTPUT_TOO_LARGE")
    decoder, records, remaining = json.JSONDecoder(), [], output.strip()
    while remaining:
        item, end = decoder.raw_decode(remaining)
        records.extend(item if isinstance(item, list) else [item])
        remaining = remaining[end:].strip()
        if len(records) > 100:
            raise ValueError("PROVENANCE_OUTPUT_TOO_LARGE")
    for record in records:
        try:
            raw = base64.b64decode(record["payload"], validate=True)
            if len(raw) > 65536:
                continue
            item = json.loads(raw)
            if item.get("_type") not in {
                "https://in-toto.io/Statement/v1",
                "https://in-toto.io/Statement/v0.1",
            }:
                continue
            dependencies = item["predicate"]["buildDefinition"]["resolvedDependencies"]
            materials = {
                key: dependencies[index]["digest"]["sha256"]
                for key, index in zip(MATERIALS, [1, 2, 3])
            }
            expected = statement(run, acr, source, digest, materials)
            expected["_type"] = item["_type"]
            if item == expected:
                return item
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            continue
    raise ValueError("PROVENANCE_BINDING_MISMATCH")


def verify(image, source, run, acr, evidence, execute):
    hosted_runner(run["id"], execute)
    output = execute(verify_command(image, source), timeout=180)
    item = verified_statement(output, run, acr, source, image.split("@", 1)[1])
    (Path(evidence) / "verified-provenance.json").write_text(json.dumps(item, indent=2) + "\n")
    return {
        "qualified": True,
        "predicate_type": PREDICATE,
        "evidence_type": "sigstore_verified_GitHub_orchestration_of_ACR",
        "runner": "github-hosted",
        "limits": "Not an ACR-signed isolated builder statement, reproducible-build guarantee or SLSA level claim.",
    }

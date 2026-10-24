import base64
import copy
import importlib
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
proof = importlib.import_module("image_provenance")
builder = importlib.import_module("build_demo_image")
installer = importlib.import_module("install_cosign")
SOURCE, DIGEST = "a" * 40, "sha256:" + "b" * 64
IMAGE = proof.IMAGE + "@" + DIGEST


def records():
    run = {
        "id": 123,
        "run_attempt": 1,
        "head_sha": SOURCE,
        "head_branch": "main",
        "event": "workflow_run",
        "path": ".github/workflows/deploy-azure.yml",
        "repository": {"full_name": proof.REPO},
        "status": "in_progress",
        "conclusion": None,
    }
    acr = {
        "runId": "cbb",
        "status": "Succeeded",
        "outputImages": [
            {
                "registry": "cepiodemo31d48.azurecr.io",
                "repository": "cepio",
                "digest": DIGEST,
                "tag": SOURCE + "-123-1",
            }
        ],
    }
    return run, acr


def materials():
    return dict(zip(proof.MATERIALS, ["c" * 64, "d" * 64, "e" * 64]))


def envelope(item):
    return json.dumps(
        {
            "payloadType": "application/vnd.in-toto+json",
            "payload": base64.b64encode(json.dumps(item).encode()).decode(),
        }
    )


def jobs():
    return {
        "total_count": 1,
        "jobs": [
            {"name": "deploy", "runner_group_name": "GitHub Actions", "labels": ["ubuntu-latest"]}
        ],
    }


@pytest.mark.parametrize("schema", ["v1", "v0.1"])
def test_verified_statement_matches_exact_image_source_and_invocation(schema):
    run, acr = records()
    item = proof.statement(run, acr, SOURCE, DIGEST, materials())
    item["_type"] = "https://in-toto.io/Statement/" + schema
    assert proof.verified_statement(envelope(item), run, acr, SOURCE, DIGEST) == item
    assert (
        item["predicate"]["buildDefinition"]["resolvedDependencies"][1]["uri"]
        == "clean-git-source.tar"
    )


@pytest.mark.parametrize(
    "field",
    [
        "subject_name",
        "digest",
        "source",
        "builder",
        "invocation",
        "material_uri",
        "material_hash",
        "predicate",
        "schema",
        "extra",
    ],
)
def test_signed_but_mismatched_provenance_never_qualifies(field):
    run, acr = records()
    item = proof.statement(run, acr, SOURCE, DIGEST, materials())
    definition = item["predicate"]["buildDefinition"]
    if field == "subject_name":
        item["subject"][0]["name"] = "other/image"
    if field == "digest":
        item["subject"][0]["digest"]["sha256"] = "f" * 64
    if field == "source":
        definition["resolvedDependencies"][0]["digest"]["gitCommit"] = "f" * 40
    if field == "builder":
        item["predicate"]["runDetails"]["builder"]["id"] = "other"
    if field == "invocation":
        item["predicate"]["runDetails"]["metadata"]["invocationId"] += "-other"
    if field == "material_uri":
        definition["resolvedDependencies"][1]["uri"] = "caller-input"
    if field == "material_hash":
        definition["resolvedDependencies"][1]["digest"]["sha256"] = "invalid"
    if field == "predicate":
        item["predicateType"] = "custom"
    if field == "schema":
        item["_type"] = "unknown"
    if field == "extra":
        item["subject"].append(copy.deepcopy(item["subject"][0]))
    with pytest.raises(ValueError, match="PROVENANCE_BINDING_MISMATCH"):
        proof.verified_statement(envelope(item), run, acr, SOURCE, DIGEST)


@pytest.mark.parametrize("raw", ["", "{}", "not json", '{"payload":"not base64"}', "[]"])
def test_missing_or_malformed_verified_output_fails(raw):
    with pytest.raises(ValueError):
        proof.verified_statement(raw, *records(), SOURCE, DIGEST)


def test_verifier_keeps_exact_identity_claims_and_no_insecure_overrides():
    args = proof.verify_command(IMAGE, SOURCE)
    assert args[args.index("--certificate-identity") + 1] == proof.WORKFLOW + "@refs/heads/main"
    assert args[args.index("--certificate-github-workflow-sha") + 1] == SOURCE
    assert args[args.index("--certificate-github-workflow-trigger") + 1] == "workflow_run"
    assert "--check-claims=true" in args
    assert not any("ignore" in a or "regexp" in a or "insecure" in a for a in args)
    with pytest.raises(ValueError):
        proof.verify_command("repo:latest", SOURCE)


@pytest.mark.parametrize("bad", ["self-hosted", "group", "missing", "multiple"])
def test_untrusted_runners_are_rejected(bad):
    data = jobs()
    if bad == "self-hosted":
        data["jobs"][0]["labels"].append("self-hosted")
    if bad == "group":
        data["jobs"][0]["runner_group_name"] = "custom"
    if bad == "missing":
        data["jobs"] = []
    if bad == "multiple":
        data["total_count"] = 2
    with pytest.raises(ValueError):
        proof.hosted_runner(123, lambda args: json.dumps(data))


@pytest.mark.parametrize("failure", [None, "signature", "binding"])
def test_only_successful_signature_and_binding_write_verified_evidence(tmp_path, failure):
    run, acr = records()
    item = proof.statement(run, acr, SOURCE, DIGEST, materials())
    if failure == "binding":
        item["subject"][0]["name"] = "other"

    def execute(args, **kwargs):
        if args[0] == "gh":
            return json.dumps(jobs())
        assert args == proof.verify_command(IMAGE, SOURCE)
        if failure == "signature":
            raise ValueError("COMMAND_FAILED")
        return envelope(item)

    if failure:
        with pytest.raises(ValueError):
            proof.verify(IMAGE, SOURCE, run, acr, tmp_path, execute)
        assert not (tmp_path / "verified-provenance.json").exists()
    else:
        assert proof.verify(IMAGE, SOURCE, run, acr, tmp_path, execute)["qualified"]
        assert json.loads((tmp_path / "verified-provenance.json").read_text()) == item


@pytest.mark.parametrize("failure", [None, "sign", "verify", "dirty", "run", "acr_digest"])
def test_build_outputs_withheld_until_signing_and_verification(monkeypatch, tmp_path, failure):
    monkeypatch.chdir(tmp_path)
    for name in ["Dockerfile", ".dockerignore"]:
        Path(name).write_text("committed source")
    temporary = tmp_path / "runner"
    temporary.mkdir()
    for name, value in {
        "DEPLOY_SHA": SOURCE,
        "GITHUB_SHA": SOURCE,
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_REPOSITORY": proof.REPO,
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_EVENT_NAME": "workflow_run",
        "AZURE_CONTAINER_REGISTRY": "cepiodemo31d48",
        "RUNNER_TEMP": str(temporary),
        "GITHUB_OUTPUT": str(tmp_path / "outputs"),
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setenv("DOCKER_CONFIG", "original")
    run, acr = records()
    if failure == "run":
        run["head_sha"] = "f" * 40
    calls = []

    def command(args, **kwargs):
        calls.append(args)
        if args[:3] == ["git", "rev-parse", "HEAD"]:
            return SOURCE
        if args[:2] == ["git", "status"]:
            return "dirty" if failure == "dirty" else ""
        if args[:2] == ["git", "ls-files"]:
            return ""
        if args[:2] == ["git", "archive"]:
            Path(args[args.index("--output") + 1]).write_bytes(b"git source archive")
            return ""
        if args[:2] == ["gh", "api"]:
            return json.dumps(jobs() if "/jobs?" in args[2] else run)
        if args[:3] == ["az", "acr", "build"]:
            return json.dumps({"runId": "cbb"})
        if args[:4] == ["az", "acr", "task", "show-run"]:
            return json.dumps(acr)
        if args[:4] == ["az", "acr", "repository", "show"]:
            return "sha256:" + "f" * 64 if failure == "acr_digest" else DIGEST
        if args[:3] == ["az", "acr", "login"]:
            return json.dumps({"accessToken": "SECRET"})
        if "--password-stdin" in args:
            assert kwargs["stdin"] == "SECRET"
            return ""
        assert args[:2] == ["cosign", "attest"] and args[-1] == IMAGE
        assert "github-actions" in args and "--identity-token" not in args
        if failure == "sign":
            raise ValueError("COMMAND_FAILED")
        return ""

    def verify(*args):
        if failure == "verify":
            raise ValueError("COMMAND_FAILED")
        return {"qualified": True}

    monkeypatch.setattr(builder, "command", command)
    monkeypatch.setattr(builder, "verify", verify)
    if failure:
        with pytest.raises(ValueError):
            builder.main()
        assert not (tmp_path / "outputs").exists()
    else:
        builder.main()
        assert IMAGE in (tmp_path / "outputs").read_text()
        assert (temporary / "cepio-provenance/provenance.json").exists()
    assert builder.os.environ["DOCKER_CONFIG"] == "original"
    if failure in {"dirty", "run"}:
        assert not any(args[:3] == ["az", "acr", "build"] for args in calls)
    assert not any("grant" in args or "role" in args or "webapp" in args for args in calls)


def test_pinned_tool_rejects_changed_download_before_writing(monkeypatch, tmp_path):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self, size):
            return b"tampered"

    monkeypatch.setattr(installer.urllib.request, "urlopen", lambda *a, **k: Response())
    with pytest.raises(ValueError, match="CHECKSUM_MISMATCH"):
        installer.download("cosign-linux-amd64", tmp_path / "tool")
    assert not (tmp_path / "tool").exists()


def test_deployment_sign_verify_and_retention_precede_mutation_without_new_permissions():
    import yaml

    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/deploy-azure.yml").read_text())
    job = workflow["jobs"]["deploy"]
    assert job["permissions"] == {"contents": "read", "id-token": "write"}
    steps = job["steps"]
    build = next(i for i, s in enumerate(steps) if s.get("id") == "build")
    upload = next(
        i
        for i, s in enumerate(steps)
        if s.get("with", {}).get("name", "").startswith("cepio-image-provenance")
    )
    deploy = next(i for i, s in enumerate(steps) if s.get("name") == "Deploy immutable image")
    assert build < upload < deploy
    assert steps[build]["run"] == "python3 scripts/build_demo_image.py"

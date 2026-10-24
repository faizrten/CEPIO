import importlib.util
import json
from pathlib import Path

import pytest


def module(name):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parents[1] / "scripts" / (name + ".py")
    )
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


minimizer = module("minimize_runtime")
provenance = module("propose_image_provenance")


def runtime(root):
    for name in (
        "usr/bin/mount",
        "usr/bin/nsenter",
        "usr/bin/infocmp",
        "usr/bin/perl5.40.1",
        "usr/lib/perl-base/Archive/Tar.pm",
        "usr/share/perl/5.40/Pod/Text.pm",
        "usr/lib/libuuid.so",
        "usr/lib/libtinfo.so",
        "usr/bin/python",
        "bin/sh",
        "var/lib/dpkg/status",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("retained inventory or code")


def test_minimization_removes_entrypoints_not_libraries_or_inventory(tmp_path):
    runtime(tmp_path)
    before = minimizer.inventory_hash(tmp_path)
    result = minimizer.minimize(tmp_path)
    assert result["unused_entrypoints_absent"] and result["removed_path_count"] == 6
    assert not result["vulnerability_waiver"]
    assert minimizer.inventory_hash(tmp_path) == before
    for name in ("usr/lib/libuuid.so", "usr/lib/libtinfo.so", "usr/bin/python", "bin/sh"):
        assert (tmp_path / name).is_file()


@pytest.mark.parametrize("failure", ["entrypoint", "inventory", "waiver"])
def test_runtime_regressions_fail_closed(tmp_path, failure):
    runtime(tmp_path)
    minimizer.minimize(tmp_path)
    if failure == "entrypoint":
        (tmp_path / "usr/bin/nsenter").write_text("regression")
    elif failure == "inventory":
        (tmp_path / "var/lib/dpkg/status").write_text("hidden packages")
    else:
        path = tmp_path / minimizer.MANIFEST
        data = json.loads(path.read_text())
        data["vulnerability_waiver"] = True
        path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        minimizer.verify(tmp_path)


def test_minimization_refuses_parent_path_escape(tmp_path, monkeypatch):
    runtime(tmp_path)
    monkeypatch.setattr(minimizer, "candidates", lambda root: [root.parent / "outside"])
    with pytest.raises(ValueError, match="ESCAPES_ROOT"):
        minimizer.minimize(tmp_path)


def records():
    source, digest = "a" * 40, "sha256:" + "b" * 64
    run = {
        "id": 123,
        "run_attempt": 1,
        "head_sha": source,
        "head_branch": "main",
        "event": "workflow_run",
        "path": ".github/workflows/deploy-azure.yml",
        "repository": {"full_name": "faizrten/CEPIO"},
        "status": "in_progress",
        "conclusion": None,
    }
    acr = {
        "runId": "cb9",
        "status": "Succeeded",
        "outputImages": [
            {
                "registry": "cepiodemo31d48.azurecr.io",
                "repository": "cepio",
                "digest": digest,
                "tag": source + "-123-1",
            }
        ],
    }
    return run, acr, source, digest


def test_unsigned_proposal_binds_exact_subject_source_context_and_run():
    run, acr, source, digest = records()
    result = provenance.proposal(run, acr, source, digest, "c" * 64, "d" * 64)
    assert result["status"] == "UNSIGNED_PROPOSAL_NOT_EVIDENCE"
    statement = result["statement"]
    assert statement["subject"] == [{"name": provenance.IMAGE, "digest": {"sha256": "b" * 64}}]
    assert (
        statement["predicate"]["buildDefinition"]["resolvedDependencies"][0]["digest"]["gitCommit"]
        == source
    )


@pytest.mark.parametrize("failure", ["source", "digest", "tag", "builder", "failed", "material"])
def test_provenance_proposal_rejects_mismatched_builds(failure):
    run, acr, source, digest = records()
    context = "c" * 64
    if failure == "source":
        run["head_sha"] = "e" * 40
    if failure == "digest":
        digest = "sha256:" + "f" * 64
    if failure == "tag":
        acr["outputImages"][0]["tag"] = "latest"
    if failure == "builder":
        run["path"] = ".github/workflows/other.yml"
    if failure == "failed":
        acr["status"] = "Failed"
    if failure == "material":
        context = "caller supplied"
    with pytest.raises(ValueError):
        provenance.proposal(run, acr, source, digest, context, "d" * 64)


def test_signing_proposal_cannot_activate_or_broaden_existing_workflows():
    import yaml

    root = Path(__file__).resolve().parents[1]
    design = yaml.safe_load((root / "docs/proposals/demo-exact-image-provenance.yaml").read_text())
    assert design["status"] == "inactive_permission_review_required"
    assert "jobs" not in design and "on" not in design and True not in design
    assert design["proposed_signing_step"]["with"]["push-to-registry"] is False
    assert design["proposed_signing_step"]["with"]["subject-name"] == provenance.IMAGE
    for file in ("deploy-azure.yml", "deployed-image-readonly.yml"):
        workflow = yaml.safe_load((root / ".github/workflows" / file).read_text())
        assert workflow["permissions"] == {"contents": "read"}
        for job in workflow["jobs"].values():
            assert job["permissions"] == {"contents": "read", "id-token": "write"}

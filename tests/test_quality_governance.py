"""Negative controls ensure the new gates detect representative regressions."""

import importlib.util
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

import pytest
import yaml


def load_script(name):
    path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_openapi_schema_regressions_are_detected():
    compare = load_script("check_compatibility_evidence").removed_contract
    old = {"schema": {"type": "string", "enum": ["a", "b"]}}
    assert compare(old, {"schema": {"type": "integer"}})
    assert not compare(old, {**old, "new": {}})


def test_public_signature_and_persistence_changes_are_detected():
    module = load_script("check_compatibility_evidence")
    assert module.python_contract("def query(limit=1): pass") != module.python_contract(
        "def query(limit): pass"
    )
    assert module.ddl('sql = "CREATE TABLE objects (id TEXT);"')
    assert module.ddl('sql = "CREATE TABLE objects (id TEXT);"') != module.ddl(
        'sql = "CREATE TABLE objects (id INT);"'
    )


def test_security_exceptions_cannot_hide_new_sql_in_same_file():
    module = load_script("check_security")
    issue = {
        "filename": "src/cepio/query_backend.py",
        "test_id": "B608",
        "issue_text": "Possible SQL injection",
        "issue_severity": "MEDIUM",
        "issue_confidence": "LOW",
        "code": "76 SELECT trusted\n77 bound parameters\n",
    }
    moved = dict(issue, code="90 SELECT trusted\n91 bound parameters\n")
    injected = dict(issue, code="76 SELECT untrusted\n77 concatenated user input\n")
    assert not module.unexpected([moved], [issue])
    assert module.unexpected([injected], [issue])
    assert module.unexpected([issue, issue], [issue])


def test_trusted_base_governance_guard_accepts_evidence_and_rejects_bypasses():
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is supplied by GitHub-hosted runners")
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load(
        (root / ".github/workflows/governance-protection.yml").read_text(encoding="utf-8")
    )
    script = workflow["jobs"]["protection"]["steps"][0]["with"]["script"]
    harness = r"""
      const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
      const guard = new AsyncFunction('context', 'github', 'core', process.argv[1]);
      async function check(body, files) {
        const failures=[];
        const summary={addHeading(){return this},addList(){return this},async write(){}};
        await guard({payload:{pull_request:{body,number:1}},repo:{}},
          {paginate:async()=>files,rest:{pulls:{listFiles(){}}}},
          {setFailed:msg=>failures.push(msg),summary});
        return failures;
      }
      const high='## Risk classification\n\n- [x] high\n\n## Governance changes\n\n- [x] Existing gates remain enforced.\n\nPreserve all pre-existing controls and require evidence for changed workflows; see ADR for rationale and validation.\n\n## Other\n';
      const files=[{filename:'.github/workflows/quality.yml',status:'modified'},
        {filename:'docs/adr/ADR-0008-quality.md',status:'modified'}];
      if ((await check(high,files)).length) throw Error('Valid change rejected');
      for (const [body, paths] of [
        [high.replace('[x] high','[x] low'),files],
        [high,files.slice(0,1)],
        [high.replace('[x] Existing','[ ] Existing'),files],
        [high+'\n- [x] CUSTOMER CONFIDENTIAL',files],
        [high.replace('- [x] high','- [x] high\n- [x] low'),files],
        [high.replace('[x] high','[x] low'),[{filename:'renamed.yml',previous_filename:'.github/workflows/quality.yml'}]]
      ]) {
        if (!(await check(body,paths)).length) throw Error('Bypass accepted');
      }
      if ((await check('## Risk classification\n\n- [x] low\n', [{filename:'docs/example.md'}])).length) throw Error('Routine low-risk change rejected');
    """
    subprocess.run(
        [node, "--input-type=module", "-e", harness, script],
        check=True,
        capture_output=True,
        text=True,
    )


def test_release_qualification_manifest_and_version_fail_closed(tmp_path, monkeypatch):
    module = load_script("qualify_release")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module.subprocess, "check_output", lambda *args, **kwargs: "abc123\n")
    for path in ["dist", "evidence", "docs"]:
        (tmp_path / path).mkdir()
    (tmp_path / "RELEASE.md").write_text("Developer Preview notes")
    (tmp_path / "docs/migrations-and-compatibility.md").write_text("No migration required")
    wheel = tmp_path / f"dist/cepio-{module.__version__}-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    (tmp_path / "dist/cepio-container.tar").write_bytes(b"container")
    for filename in ["container-sbom.json", "container-vulnerabilities.json", "python-sbom.json"]:
        (tmp_path / "evidence" / filename).write_text("{}")
    monkeypatch.setattr(sys, "argv", ["qualify_release.py", "--tag", f"v{module.__version__}"])
    assert module.main() == 0
    report = json.loads((tmp_path / "evidence/release-manifest.json").read_text())
    assert report["qualification"] == "developer-preview"
    assert report["production_qualified"] is False
    assert (
        report["artifacts"][wheel.relative_to(tmp_path).as_posix()]
        == hashlib.sha256(b"wheel").hexdigest()
    )
    monkeypatch.setattr(sys, "argv", ["qualify_release.py", "--tag", "v999.0.0"])
    with pytest.raises(ValueError, match="does not match"):
        module.main()
